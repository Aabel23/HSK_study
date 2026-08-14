"""Deciding whether a generated exam question is fit to ship.

The question bank is grown by `scripts/generate_bank.py`, which asks Gemini for
new items. A language model will happily return a fill-in-the-blank sentence
with no blank in it, a multiple-choice question whose answer is missing from the
options, or an HSK 2 passage written in HSK 6 vocabulary — all of which look
plausible until a learner meets them mid-exam.

So nothing reaches the bank on the model's word. Every generated item is checked
here first, and anything that fails is dropped rather than repaired: a
regenerated item costs one more API call, while a subtly broken one costs the
learner's trust in the exam.

The checks fall into three groups:

* **Shape** — the fields the runtime reads exist and hold the right types. A
  missing `answer` would crash grading; a missing `explanation_vi` would leave
  the learner with a wrong mark and no reason for it.
* **Self-consistency** — the answer actually solves the question. This is where
  models fail most often and where the failure is least visible.
* **Level** — the Chinese used is vocabulary the learner is supposed to know at
  that level, measured against the 10,969-word bank already in the database.

The Vietnamese explanations reuse :mod:`scripts.meaning_quality`, so "is this
real Vietnamese?" keeps exactly one definition in this project.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from scripts.meaning_quality import is_english_gloss


#: Marks the gap in a fill-in-the-blank sentence, in either width of bracket.
BLANK_PATTERN = re.compile(r"[(（]\s*[)）]")

#: The star the real HSK paper prints in front of a true/false statement.
JUDGE_MARK = "★"

#: Clauses of a reordering answer are joined by this, matching reading_service.
ORDER_SEPARATOR = "|"

#: Share of a passage's characters that must be at or below the target level
#: before the item counts as level-appropriate. Not 100%: real HSK papers do use
#: the odd name or connective from above the level, and the character bank has
#: gaps of its own.
LEVEL_COVERAGE_FLOOR = 0.85

_CJK = re.compile(r"[一-鿿]")


@dataclass
class Report:
    """The verdict on one item, with every reason it was rejected."""

    item_id: str
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def fail(self, problem: str) -> None:
        self.problems.append(problem)


def chinese_characters(text: str) -> list[str]:
    return _CJK.findall(text or "")


def _require_chinese(report: Report, field_name: str, value: Any, minimum: int = 2) -> str:
    """Check a field holds a real string of Chinese, and return it."""
    if not isinstance(value, str) or not value.strip():
        report.fail(f"thiếu trường '{field_name}'")
        return ""
    if len(chinese_characters(value)) < minimum:
        report.fail(f"'{field_name}' không phải tiếng Trung")
    return value.strip()


def _require_vietnamese(report: Report, field_name: str, value: Any) -> None:
    """Learner-facing prose must be Vietnamese, per the project's language rule."""
    if not isinstance(value, str) or not value.strip():
        report.fail(f"thiếu trường '{field_name}'")
        return
    if chinese_characters(value) and len(chinese_characters(value)) > len(value) / 2:
        report.fail(f"'{field_name}' viết bằng tiếng Trung chứ không phải tiếng Việt")
        return
    if is_english_gloss(value, None, ""):
        report.fail(f"'{field_name}' còn lẫn tiếng Anh")


def level_coverage(text: str, known_characters: frozenset[str]) -> float:
    """Fraction of the text's Chinese characters that the learner should know."""
    characters = chinese_characters(text)
    if not characters:
        return 1.0
    known = sum(1 for character in characters if character in known_characters)
    return known / len(characters)


def _check_level(
    report: Report, text: str, known_characters: frozenset[str], label: str
) -> None:
    if not known_characters:  # no bank loaded; skip rather than reject everything
        return
    coverage = level_coverage(text, known_characters)
    if coverage < LEVEL_COVERAGE_FLOOR:
        unknown = sorted(
            {c for c in chinese_characters(text) if c not in known_characters}
        )
        report.fail(
            f"{label} dùng chữ trên trình độ ({coverage:.0%} trong vốn từ, "
            f"lạ: {''.join(unknown[:8])})"
        )


# ---------------------------------------------------------------------------
# Per-question-type checks
# ---------------------------------------------------------------------------


def _check_judge(report: Report, item: dict[str, Any], known: frozenset[str]) -> None:
    passage = _require_chinese(report, "passage_zh", item.get("passage_zh"), minimum=4)
    statement = _require_chinese(report, "statement_zh", item.get("statement_zh"), minimum=3)
    if statement and not statement.startswith(JUDGE_MARK):
        report.fail(f"'statement_zh' phải bắt đầu bằng {JUDGE_MARK}")
    if not isinstance(item.get("answer"), bool):
        report.fail("'answer' phải là true hoặc false")
    _check_level(report, passage + statement, known, "đoạn văn")


def _check_fill_blank(report: Report, item: dict[str, Any], known: frozenset[str]) -> None:
    sentence = _require_chinese(report, "sentence_zh", item.get("sentence_zh"), minimum=3)
    if sentence and not BLANK_PATTERN.search(sentence):
        report.fail("'sentence_zh' không có chỗ trống dạng (  )")
    answer = item.get("answer")
    if not isinstance(answer, str) or not chinese_characters(answer):
        report.fail("'answer' phải là một từ tiếng Trung")
        return
    # The answer showing up in the visible sentence gives the blank away.
    if sentence and answer in BLANK_PATTERN.sub("", sentence):
        report.fail("'answer' đã lộ ngay trong câu")
    _check_level(report, sentence + answer, known, "câu")


def _check_multiple_choice(
    report: Report, item: dict[str, Any], known: frozenset[str]
) -> None:
    passage = _require_chinese(report, "passage_zh", item.get("passage_zh"), minimum=5)
    question = _require_chinese(report, "question_zh", item.get("question_zh"), minimum=2)

    options = item.get("options")
    if not isinstance(options, list) or len(options) < 3:
        report.fail("'options' phải có ít nhất 3 lựa chọn")
        return
    if len(set(options)) != len(options):
        report.fail("'options' có lựa chọn trùng nhau")
    answer = item.get("answer")
    if answer not in options:
        report.fail("'answer' không nằm trong 'options'")
    _check_level(report, passage + question + "".join(map(str, options)), known, "bài đọc")


def _check_reordering(report: Report, item: dict[str, Any], known: frozenset[str]) -> None:
    clauses = item.get("words_zh")
    if not isinstance(clauses, list) or len(clauses) < 3:
        report.fail("'words_zh' phải có ít nhất 3 cụm")
        return
    if len(set(clauses)) != len(clauses):
        report.fail("'words_zh' có cụm trùng nhau")
    answer = item.get("answer")
    if not isinstance(answer, str):
        report.fail("'answer' phải là chuỗi các cụm nối bằng '|'")
        return
    ordered = answer.split(ORDER_SEPARATOR)
    if sorted(ordered) != sorted(str(clause) for clause in clauses):
        report.fail("'answer' không phải là hoán vị của 'words_zh'")
    _check_level(report, "".join(map(str, clauses)), known, "câu")


def _check_spoken(report: Report, item: dict[str, Any], known: frozenset[str]) -> None:
    """HSKK items: a line to say, its pinyin, and what it means."""
    hanzi = _require_chinese(report, "hanzi", item.get("hanzi"), minimum=2)
    pinyin = item.get("pinyin")
    if not isinstance(pinyin, str) or not pinyin.strip():
        report.fail("thiếu trường 'pinyin'")
    elif chinese_characters(pinyin):
        report.fail("'pinyin' còn lẫn chữ Hán")
    _require_vietnamese(report, "vi", item.get("vi"))
    _check_level(report, hanzi, known, "câu nói")


CHECKS = {
    "judge_true_false": _check_judge,
    "fill_in_blank_sentence": _check_fill_blank,
    "multiple_choice_dialogue": _check_multiple_choice,
    "reading_comprehension": _check_multiple_choice,
    "sentence_reordering": _check_reordering,
    "repeat": _check_spoken,
    "answer": _check_spoken,
    "speak": _check_spoken,
    "opinion": _check_spoken,
    "describe": _check_spoken,
}

#: Types whose learner-facing explanation must be Vietnamese prose.
_NEEDS_EXPLANATION = frozenset(
    {
        "judge_true_false",
        "fill_in_blank_sentence",
        "multiple_choice_dialogue",
        "reading_comprehension",
        "sentence_reordering",
    }
)


def check(item: dict[str, Any], question_type: str, known_characters: frozenset[str]) -> Report:
    """Run every applicable check over one generated item."""
    report = Report(item_id=str(item.get("id") or "?"))

    checker = CHECKS.get(question_type)
    if checker is None:
        report.fail(f"không biết cách kiểm tra loại '{question_type}'")
        return report

    checker(report, item, known_characters)
    if question_type in _NEEDS_EXPLANATION:
        _require_vietnamese(report, "explanation_vi", item.get("explanation_vi"))
    return report


def fingerprint(item: dict[str, Any], question_type: str) -> str:
    """A stable identity for an item, used to reject near-duplicates.

    Built from the Chinese the learner actually reads, with punctuation and
    whitespace stripped, so "他很忙。" and "他很忙!" count as the same question.
    The id is deliberately excluded — two items with different ids and identical
    text are exactly the duplication this is meant to catch.
    """
    fields = ("passage_zh", "statement_zh", "sentence_zh", "question_zh", "hanzi")
    parts = [str(item.get(name, "")) for name in fields]
    if isinstance(item.get("words_zh"), list):
        parts.extend(str(clause) for clause in item["words_zh"])
    return "".join(chinese_characters("".join(parts)))


def duplicate_keys(items: Iterable[dict[str, Any]], question_type: str) -> set[str]:
    return {fingerprint(item, question_type) for item in items}
