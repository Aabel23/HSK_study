"""The reading half of the HSK mock exam, built like the real 阅读 section.

This replaced a run of generated vocabulary multiple-choice questions. Those
tested recall of single words; the real exam tests reading — judging a statement
against a sentence, picking the word a sentence needs, ordering clauses into a
coherent paragraph, and answering about a short passage.

Two rules shape the design:

* **Answers never leave the server.** The paper sent to the browser carries no
  `answer` field, and :func:`check_answer` is what decides right or wrong. The
  old multiple-choice flow shipped the correct id to the client, which meant the
  answer key was one devtools panel away.
* **Fill-in-the-blank parts get a shared word bank** with exactly one spare word,
  the convention the real paper uses, so the last blank is still a decision.
"""

from __future__ import annotations

import json
import random
from functools import lru_cache
from typing import Any

from backend.services import item_pool
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from scripts.seed_data import FULL_DATA_DIR


BANK_FILE = "hsk_reading_bank.json"

#: Clauses of a reordering question are joined by this when stored and compared.
ORDER_SEPARATOR = "|"

#: Word banks carry one more word than there are blanks.
SPARE_WORDS = 1


@lru_cache(maxsize=1)
def _load_bank() -> dict[str, Any]:
    path = FULL_DATA_DIR / BANK_FILE
    if not path.is_file():
        raise InvalidOperationError("Không tìm thấy ngân hàng đề đọc.")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _get_level(exam_level: str) -> dict[str, Any]:
    level = _load_bank()["levels"].get(exam_level)
    if not level:
        raise ResourceNotFoundError("Không có phần đọc cho cấp độ này.")
    return level


def describe(exam_level: str) -> dict[str, Any]:
    """Section summary for the intro screen: no questions, so no answers to leak."""
    level = _get_level(exam_level)
    return {
        "hsk_level": level["hsk_level"],
        "section_name_zh": level["section_name_zh"],
        "section_name_vi": level["section_name_vi"],
        "time_minutes": level["time_minutes"],
        "total_questions": sum(part["count"] for part in level["parts"]),
        "parts": [
            {
                "part_number": part["part_number"],
                "question_type": part["question_type"],
                "instruction_zh": part["instruction_zh"],
                "instruction_vi": part["instruction_vi"],
                "count": part["count"],
            }
            for part in level["parts"]
        ],
    }


def list_pools(exam_level: str) -> list[dict[str, Any]]:
    """The question pools behind one reading section, for the bank inventory.

    Answers are included — this is server-side bookkeeping, not part of any exam
    paper — so callers must never pass the result to a client untouched.
    """
    return [
        {
            "label": part["instruction_vi"],
            "question_type": part["question_type"],
            "draw_per_exam": part["count"],
            "items": part["pool"],
        }
        for part in _get_level(exam_level)["parts"]
    ]


def _public_question(part: dict[str, Any], item: dict[str, Any], index: int) -> dict[str, Any]:
    """Strip a bank entry down to what the exam paper may show."""
    question: dict[str, Any] = {"id": item["id"], "question_index": index}
    kind = part["question_type"]

    if kind == "judge_true_false":
        question["passage_zh"] = item["passage_zh"]
        question["statement_zh"] = item["statement_zh"]
    elif kind == "fill_in_blank_sentence":
        question["sentence_zh"] = item["sentence_zh"]
    elif kind == "sentence_reordering":
        # Shuffled, otherwise the stored order would give the answer away.
        clauses = list(item["words_zh"])
        random.shuffle(clauses)
        question["words_zh"] = clauses
    else:  # multiple_choice_dialogue, reading_comprehension
        question["passage_zh"] = item["passage_zh"]
        question["question_zh"] = item["question_zh"]
        options = list(item["options"])
        random.shuffle(options)
        question["options"] = [
            {"key": chr(ord("A") + position), "text_zh": text}
            for position, text in enumerate(options)
        ]
    return question


def build_section(exam_level: str) -> dict[str, Any]:
    """Assemble one reading section, answers removed."""
    level = _get_level(exam_level)
    parts = []
    total = 0

    for config in level["parts"]:
        # Unseen questions first, so a second sitting is a genuinely new paper
        # rather than a reshuffle of the one before it.
        chosen = item_pool.take(config["pool"], config["count"])
        count = len(chosen)
        part: dict[str, Any] = {
            "part_id": config["part_id"],
            "part_number": config["part_number"],
            "question_type": config["question_type"],
            "instruction_zh": config["instruction_zh"],
            "instruction_vi": config["instruction_vi"],
            "question_count": count,
            "questions": [
                _public_question(config, item, index) for index, item in enumerate(chosen)
            ],
        }

        if config["question_type"] == "fill_in_blank_sentence":
            # One spare word so the final blank is still a real choice.
            answers = [item["answer"] for item in chosen]
            spares = [word for word in config.get("distractors", []) if word not in answers]
            words = answers + random.sample(spares, min(SPARE_WORDS, len(spares)))
            random.shuffle(words)
            part["word_bank"] = [
                {"key": chr(ord("A") + position), "word_zh": word}
                for position, word in enumerate(words)
            ]

        if "options_per_question" in config:
            part["options_per_question"] = config["options_per_question"]

        parts.append(part)
        total += count

    return {
        "section_id": "reading",
        "section_name_zh": level["section_name_zh"],
        "section_name_vi": level["section_name_vi"],
        "hsk_level": level["hsk_level"],
        "time_minutes": level["time_minutes"],
        "total_questions": total,
        "parts": parts,
    }


def _find(exam_level: str, question_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    for part in _get_level(exam_level)["parts"]:
        for item in part["pool"]:
            if item["id"] == question_id:
                return part, item
    raise ResourceNotFoundError("Không tìm thấy câu hỏi này trong đề đọc.")


def _normalise(value: Any) -> str:
    """Compare answers without tripping over spacing or full-width punctuation."""
    return str(value).strip().replace(" ", "").replace("　", "")


#: Which parts of a question are worth reading back once it has been answered,
#: per question type, in the order they should be shown. The learner has just
#: worked through this Chinese without help; the review is where they get to see
#: how it is pronounced and what it actually said.
_REVEAL_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "judge_true_false": (("passage_zh", "Đoạn văn"), ("statement_zh", "Nhận định")),
    "fill_in_blank_sentence": (("sentence_zh", "Câu đầy đủ"), ("answer", "Từ cần điền")),
    "multiple_choice_dialogue": (
        ("passage_zh", "Hội thoại"),
        ("question_zh", "Câu hỏi"),
        ("answer", "Đáp án"),
    ),
    "reading_comprehension": (
        ("passage_zh", "Đoạn văn"),
        ("question_zh", "Câu hỏi"),
        ("answer", "Đáp án"),
    ),
    "sentence_reordering": (("answer", "Câu hoàn chỉnh"),),
}


def _reveal(part: dict[str, Any], item: dict[str, Any], answer_text: str) -> list[dict[str, str]]:
    """Pinyin and Vietnamese for the Chinese in a question, for the review card.

    Reads the ``gloss`` block the bank carries per item. Entries with no gloss
    are skipped rather than shown bare, so an item that has not been glossed yet
    simply reveals less instead of rendering an empty row.
    """
    gloss = item.get("gloss") or {}
    lines = []
    for name, label in _REVEAL_FIELDS.get(part["question_type"], ()):
        # The reordering answer is stored clause-separated; show it as a sentence.
        text = answer_text if name == "answer" else item.get(name, "")
        entry = gloss.get(name) or {}
        if not text or not (entry.get("pinyin") or entry.get("vi")):
            continue
        lines.append(
            {
                "label_vi": label,
                "zh": str(text),
                "pinyin": str(entry.get("pinyin", "")),
                "vi": str(entry.get("vi", "")),
            }
        )
    return lines


def check_answer(exam_level: str, question_id: str, answer: Any) -> dict[str, Any]:
    """Decide whether one submitted answer is right, and explain why."""
    part, item = _find(exam_level, question_id)
    expected = item["answer"]

    if part["question_type"] == "judge_true_false":
        # Accept a real boolean as well as the strings a form control produces.
        if isinstance(answer, bool):
            given: Any = answer
        else:
            text = _normalise(answer).lower()
            if text not in {"true", "false", "1", "0", "đúng", "sai"}:
                given = None
            else:
                given = text in {"true", "1", "đúng"}
        is_correct = given is not None and given == expected
        correct_answer = "Đúng" if expected else "Sai"
        reveal_text = ""
    elif part["question_type"] == "sentence_reordering":
        # The client sends the clauses in the order the learner arranged them.
        given_order = answer if isinstance(answer, list) else str(answer).split(ORDER_SEPARATOR)
        is_correct = [_normalise(clause) for clause in given_order] == [
            _normalise(clause) for clause in expected.split(ORDER_SEPARATOR)
        ]
        correct_answer = " → ".join(expected.split(ORDER_SEPARATOR))
        reveal_text = "".join(expected.split(ORDER_SEPARATOR))
    else:
        is_correct = _normalise(answer) == _normalise(expected)
        correct_answer = str(expected)
        reveal_text = str(expected)

    return {
        "question_id": question_id,
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "explanation_vi": item["explanation_vi"],
        "reveal": _reveal(part, item, reveal_text),
    }
