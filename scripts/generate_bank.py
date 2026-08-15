"""Grow the exam question bank with Gemini, offline and under review.

The banks in ``scripts/data/`` ship with the app and are the only thing a mock
exam draws from, so their size is the ceiling on how many genuinely different
papers a learner can sit. Writing hundreds of HSK reading passages by hand is
not realistic; asking a model for them is — provided nothing it returns is
trusted.

This runs as a **build-time tool, never at request time**. The learner's exam
never waits on a network call, never needs an API key, and never meets a
question that has not already passed :mod:`scripts.content_quality` and, if you
want, your own eye. What ships is a bigger JSON file, reviewed like any other
change to the repository.

Three things keep the output from drifting into slop:

* **Level-anchored prompting.** The prompt carries the actual HSK word list for
  the target level out of the database, so "HSK 2 vocabulary" is a list the
  model can follow rather than a label it can guess at.
* **Anti-repetition context.** Every existing question of that type goes into
  the prompt with an instruction not to rewrite them, and anything that comes
  back matching an existing fingerprint is dropped anyway.
* **Rejection over repair.** A failed item is discarded, not patched. The reason
  is printed so a pattern of failures shows up as a prompt problem.

Usage::

    python -m scripts.generate_bank --list
    python -m scripts.generate_bank --bank reading --level beginner --count 40
    python -m scripts.generate_bank --bank hskk --level intermediate --part 1 --count 30
    python -m scripts.generate_bank --bank reading --level beginner --count 20 --dry-run

Requires ``GEMINI_API_KEY`` in the environment, the same credential the exam's
speaking grader uses. It is read from the environment only and never written
into the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import get_connection
from backend.services import gemini_service
from scripts import content_quality
from scripts.seed_data import FULL_DATA_DIR


BANK_FILES = {
    "reading": "hsk_reading_bank.json",
    "hskk": "hskk_bank.json",
}

#: HSK levels a learner is assumed to know at each exam band. Used both to pull
#: the word list for the prompt and to judge the Chinese that comes back.
LEVELS_BY_BAND = {
    "beginner": ("1", "2"),
    "intermediate": ("1", "2", "3", "4"),
}

#: Ask for items in batches. Small enough that one bad batch is cheap, large
#: enough that the shared instructions are not re-sent for every question.
BATCH_SIZE = 8

#: Give up after this many batches produce nothing usable, rather than burning
#: quota on a prompt the model cannot satisfy.
MAX_EMPTY_BATCHES = 3

#: A long generating run will meet a busy or rate-limited endpoint sooner or
#: later. Those are worth waiting out — unlike the exam grader, nobody is
#: sitting in front of this script — so batches retry with a growing pause.
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 15


SYSTEM_INSTRUCTION = """\
Bạn là chuyên gia ra đề kỳ thi HSK của Hanban, đã soạn đề nhiều năm cho người \
Việt học tiếng Trung.

Nhiệm vụ: soạn câu hỏi thi MỚI, đúng format đề thật, đúng trình độ được yêu cầu.

Nguyên tắc bắt buộc:
- Chỉ dùng từ vựng và ngữ pháp trong phạm vi trình độ được nêu. Đây là yêu cầu \
nghiêm ngặt nhất: một chữ vượt cấp làm hỏng cả câu hỏi.
- Nội dung phải tự nhiên, giống tình huống đời thường trong đề thi thật, không \
gượng ép, không phi lý.
- Mỗi câu hỏi phải có đúng MỘT đáp án đúng không thể tranh cãi.
- Phần giải thích viết bằng TIẾNG VIỆT tự nhiên, ngắn gọn, nói rõ vì sao đáp án \
đó đúng. Tuyệt đối không viết giải thích bằng tiếng Anh.
- KHÔNG được viết lại, đảo chữ hay diễn đạt lại các câu hỏi đã có sẵn được liệt \
kê trong yêu cầu. Phải là tình huống và nội dung khác hẳn.

CHỈ trả về một đối tượng JSON đúng schema được yêu cầu, không kèm lời dẫn nào."""


# One schema description per question type. These are what the model is asked to
# fill in, and they mirror exactly what `reading_service` and `hskk_service`
# read back out of the bank.
SCHEMAS: dict[str, str] = {
    "judge_true_false": """\
Loại câu hỏi: 判断对错 — đọc một đoạn ngắn rồi phán đoán câu nhận định đúng hay sai.

Mỗi phần tử của "items":
{
  "passage_zh": "đoạn văn 1-2 câu, 10-30 chữ Hán",
  "statement_zh": "★ câu nhận định về đoạn văn",
  "answer": true hoặc false,
  "explanation_vi": "giải thích tiếng Việt vì sao đúng/sai, dẫn lại chữ trong đoạn"
}

Yêu cầu riêng: "statement_zh" LUÔN bắt đầu bằng ký tự ★ và một dấu cách. \
Khoảng một nửa số câu nên có đáp án true, một nửa false. Câu sai phải sai ở một \
chi tiết cụ thể kiểm chứng được (số lượng, thời gian, ai làm gì), không sai \
kiểu mơ hồ.""",
    "fill_in_blank_sentence": """\
Loại câu hỏi: 选词填空 — chọn từ điền vào chỗ trống trong câu.

Mỗi phần tử của "items":
{
  "sentence_zh": "câu có đúng một chỗ trống viết là (  )",
  "answer": "từ cần điền",
  "explanation_vi": "giải thích tiếng Việt vì sao từ đó hợp"
}

Yêu cầu riêng: chỗ trống viết đúng dạng (  ) với hai dấu cách. Từ cần điền \
KHÔNG được xuất hiện ở chỗ khác trong câu. Phần còn lại của câu phải đủ ngữ \
cảnh để chỉ một từ duy nhất điền được.""",
    "multiple_choice_dialogue": """\
Loại câu hỏi: đọc đoạn hội thoại ngắn rồi chọn đáp án đúng.

Mỗi phần tử của "items":
{
  "passage_zh": "hội thoại hai lượt, dạng 男：... rồi xuống dòng 女：...",
  "question_zh": "câu hỏi về hội thoại",
  "options": ["lựa chọn 1", "lựa chọn 2", "lựa chọn 3"],
  "answer": "phải trùng đúng một phần tử trong options",
  "explanation_vi": "giải thích tiếng Việt, dẫn lại câu nói chứa đáp án"
}

Yêu cầu riêng: dùng "\\n" để xuống dòng giữa hai lượt thoại. Ba lựa chọn phải \
cùng loại với nhau (cùng là đồ uống, cùng là địa điểm, cùng là thời gian) để \
không đoán được đáp án nếu chưa đọc hội thoại.""",
    "reading_comprehension": """\
Loại câu hỏi: 阅读理解 — đọc đoạn văn rồi chọn đáp án đúng.

Mỗi phần tử của "items":
{
  "passage_zh": "đoạn văn 40-80 chữ Hán, có mở và có kết",
  "question_zh": "câu hỏi về ý chính hoặc chi tiết trong đoạn",
  "options": ["lựa chọn 1", "lựa chọn 2", "lựa chọn 3", "lựa chọn 4"],
  "answer": "phải trùng đúng một phần tử trong options",
  "explanation_vi": "giải thích tiếng Việt, dẫn lại chỗ trong đoạn chứa đáp án"
}

Yêu cầu riêng: các lựa chọn sai phải nghe hợp lý với người đọc lướt — lấy chi \
tiết có thật trong đoạn nhưng trả lời sai câu hỏi.""",
    "sentence_reordering": """\
Loại câu hỏi: 排列顺序 — sắp xếp các cụm thành câu đúng thứ tự.

Mỗi phần tử của "items":
{
  "words_zh": ["cụm 1", "cụm 2", "cụm 3"],
  "answer": "cụm|cụm|cụm theo đúng thứ tự, nối bằng dấu |",
  "explanation_vi": "giải thích tiếng Việt về trật tự từ tiếng Trung ở câu này"
}

Yêu cầu riêng: "answer" phải là hoán vị đúng của "words_zh", nối bằng ký tự |. \
Mỗi câu chia thành 3-4 cụm. Chỉ có duy nhất một trật tự đúng ngữ pháp.""",
    "repeat": """\
Loại câu hỏi: 听后重复 (HSKK) — thí sinh nghe rồi nhắc lại nguyên văn.

Mỗi phần tử của "items":
{
  "hanzi": "câu ngắn 6-15 chữ Hán",
  "pinyin": "phiên âm có dấu thanh",
  "vi": "nghĩa tiếng Việt"
}

Yêu cầu riêng: câu phải là câu nói tự nhiên hằng ngày, đủ ngắn để nhắc lại \
được sau một lần nghe.""",
    "answer": """\
Loại câu hỏi: 听后回答 (HSKK) — thí sinh nghe câu hỏi rồi trả lời bằng tiếng Trung.

Mỗi phần tử của "items":
{
  "hanzi": "câu hỏi ngắn",
  "pinyin": "phiên âm có dấu thanh",
  "vi": "nghĩa tiếng Việt của câu hỏi"
}

Yêu cầu riêng: câu hỏi phải mở, trả lời được bằng 1-2 câu, về đời sống thường \
ngày (gia đình, sở thích, thói quen, thời tiết, đồ ăn).""",
    "speak": """\
Loại câu hỏi: 回答问题 (HSKK sơ cấp) — đề nói cho sẵn, thí sinh nói liền mạch.

Mỗi phần tử của "items":
{
  "hanzi": "đề bài dạng câu hỏi",
  "pinyin": "phiên âm có dấu thanh",
  "vi": "nghĩa tiếng Việt",
  "hints": ["2-4 gợi ý bằng tiếng Việt về ý nên nói"]
}

Yêu cầu riêng: đề phải nói được ít nhất 5 câu ở trình độ sơ cấp.""",
    "opinion": """\
Loại câu hỏi: 回答问题 (HSKK trung cấp) — nêu và bảo vệ quan điểm.

Mỗi phần tử của "items":
{
  "hanzi": "câu hỏi thảo luận",
  "pinyin": "phiên âm có dấu thanh",
  "vi": "nghĩa tiếng Việt",
  "hints": ["2-4 gợi ý bằng tiếng Việt về hướng lập luận"]
}

Yêu cầu riêng: câu hỏi phải có ít nhất hai phía để tranh luận, nói được 1-2 phút.""",
    "describe": """\
Loại câu hỏi: 看图说话 (HSKK trung cấp) — kể lại một tình huống.

Mỗi phần tử của "items":
{
  "hanzi": "chủ đề tình huống bằng tiếng Trung",
  "pinyin": "phiên âm có dấu thanh",
  "vi": "mô tả tình huống bằng tiếng Việt để thí sinh hình dung",
  "hints": ["2-4 gợi ý bằng tiếng Việt"]
}

Yêu cầu riêng: tình huống phải kể được theo trình tự mở - thân - kết.""",
}


# ---------------------------------------------------------------------------
# Reading the bank
# ---------------------------------------------------------------------------


def _bank_path(bank: str) -> Path:
    return FULL_DATA_DIR / BANK_FILES[bank]


def _load(bank: str) -> dict[str, Any]:
    with _bank_path(bank).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save(bank: str, data: dict[str, Any]) -> None:
    with _bank_path(bank).open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _pools(data: dict[str, Any], bank: str, level: str) -> dict[str, dict[str, Any]]:
    """Every generatable pool in one level, keyed by the ``--part`` argument.

    The two banks store their pools differently — reading nests them under
    ``parts``, HSKK keeps a separate ``pools`` map — so this is where the shapes
    are reconciled and the rest of the script sees one thing.
    """
    band = data["levels"].get(level)
    if not band:
        raise SystemExit(f"Cấp độ '{level}' không có trong bank '{bank}'.")

    if bank == "reading":
        return {
            str(part["part_number"]): {
                "question_type": part["question_type"],
                "items": part["pool"],
                "label": part["instruction_vi"],
            }
            for part in band["parts"]
        }
    return {
        str(part["part"]): {
            "question_type": part["kind"],
            "items": band["pools"][str(part["part"])],
            "label": part["title"],
        }
        for part in band["parts"]
    }


def _id_prefix(items: list[dict[str, Any]]) -> str:
    """Reuse the pool's existing id scheme so new items look native to it."""
    for item in items:
        identifier = str(item.get("id", ""))
        if "-" in identifier:
            return identifier.rsplit("-", 1)[0]
    return "gen"


def _next_ids(items: list[dict[str, Any]], count: int) -> list[str]:
    prefix = _id_prefix(items)
    highest = 0
    for item in items:
        tail = str(item.get("id", "")).rsplit("-", 1)[-1]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return [f"{prefix}-{highest + offset:02d}" for offset in range(1, count + 1)]


# ---------------------------------------------------------------------------
# Level vocabulary, pulled from the database the app already ships
# ---------------------------------------------------------------------------


def _level_vocabulary(levels: tuple[str, ...]) -> list[tuple[str, str, str]]:
    placeholders = ",".join("?" * len(levels))
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT hanzi, pinyin, meaning
            FROM vocabulary
            WHERE hsk_level IN ({placeholders})
            ORDER BY hsk_level, id
            """,
            list(levels),
        ).fetchall()
    return [(row["hanzi"], row["pinyin"], row["meaning"]) for row in rows]


def _known_characters(words: list[tuple[str, str, str]]) -> frozenset[str]:
    return frozenset("".join(hanzi for hanzi, _, _ in words))


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------


def _existing_text(items: list[dict[str, Any]], limit: int = 60) -> str:
    """A compact digest of what the pool already holds, to steer away from it."""
    lines = []
    for item in items[-limit:]:
        for name in ("passage_zh", "sentence_zh", "hanzi"):
            if item.get(name):
                lines.append(str(item[name]).replace("\n", " / "))
                break
        else:
            if isinstance(item.get("words_zh"), list):
                lines.append("".join(str(part) for part in item["words_zh"]))
    return "\n".join(f"- {line}" for line in lines)


def _build_prompt(
    question_type: str,
    band: str,
    hsk_levels: tuple[str, ...],
    words: list[tuple[str, str, str]],
    existing: list[dict[str, Any]],
    count: int,
) -> str:
    # The full HSK 1-4 list is thousands of words and would dominate the prompt;
    # the head of each level is the high-frequency core, which is what exam
    # questions at that level are actually built from.
    sample = words[: 400 * len(hsk_levels)]
    vocabulary = "、".join(hanzi for hanzi, _, _ in sample)

    return f"""\
{SCHEMAS[question_type]}

TRÌNH ĐỘ: HSK {'-'.join(hsk_levels)} (bậc {band}).

VỐN TỪ ĐƯỢC PHÉP DÙNG (chỉ dùng chữ trong danh sách này, cộng tên riêng thông dụng):
{vocabulary}

CÁC CÂU HỎI ĐÃ CÓ TRONG NGÂN HÀNG ĐỀ — không được lặp lại, không được diễn đạt lại:
{_existing_text(existing) or '(chưa có câu nào)'}

Hãy soạn {count} câu hỏi MỚI, mỗi câu một tình huống khác nhau.
Trả về JSON đúng dạng: {{"items": [ ... ]}}"""


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate(
    bank: str,
    level: str,
    part: str | None,
    count: int,
    *,
    dry_run: bool = False,
) -> int:
    """Generate, validate and append items. Returns how many were accepted."""
    data = _load(bank)
    pools = _pools(data, bank, level)

    targets = [part] if part else list(pools)
    for name in targets:
        if name not in pools:
            raise SystemExit(
                f"Phần '{name}' không có ở cấp '{level}'. Có: {', '.join(pools)}"
            )

    hsk_levels = LEVELS_BY_BAND.get(level, ("1", "2", "3", "4"))
    words = _level_vocabulary(hsk_levels)
    known = _known_characters(words)
    if not words:
        print("! Database chưa có từ vựng — chạy scripts/seed_data.py trước.")

    total_accepted = 0
    for name in targets:
        pool = pools[name]
        accepted = _fill_pool(
            pool, level, hsk_levels, words, known, count, dry_run=dry_run
        )
        total_accepted += len(accepted)

    if total_accepted and not dry_run:
        _save(bank, data)
        print(f"\n✓ Đã ghi {total_accepted} câu mới vào {_bank_path(bank).name}")
    elif dry_run:
        print(f"\n(dry-run) {total_accepted} câu đạt yêu cầu, chưa ghi vào file.")
    else:
        print("\n! Không có câu nào đạt yêu cầu.")
    return total_accepted


def _ask(
    prompt: str,
    *,
    system_instruction: str = SYSTEM_INSTRUCTION,
    # Higher than the grader's 0.2 when writing questions: variety is the entire
    # point there, and the validator catches what the extra freedom costs.
    temperature: float = 0.9,
) -> dict[str, Any] | None:
    """One batch request, waiting out a busy endpoint. ``None`` means give up."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return gemini_service.generate_json(
                system_instruction=system_instruction,
                prompt=prompt,
                temperature=temperature,
            )
        except gemini_service.TransientError as error:
            if attempt == MAX_RETRIES:
                print(f"  ! Gemini vẫn bận sau {MAX_RETRIES} lần, bỏ qua phần này.")
                return None
            pause = RETRY_BACKOFF_SECONDS * attempt
            print(f"  … {error} Thử lại sau {pause}s.")
            time.sleep(pause)
        except Exception as error:  # noqa: BLE001 - permanent; waiting will not help
            print(f"  ! Gemini lỗi, bỏ qua phần này: {error}")
            return None
    return None


def _fill_pool(
    pool: dict[str, Any],
    band: str,
    hsk_levels: tuple[str, ...],
    words: list[tuple[str, str, str]],
    known: frozenset[str],
    wanted: int,
    *,
    dry_run: bool,
) -> list[dict[str, Any]]:
    question_type = pool["question_type"]
    items = pool["items"]
    print(f"\n=== {pool['label']} ({question_type}) — đang có {len(items)} câu")

    seen = content_quality.duplicate_keys(items, question_type)
    accepted: list[dict[str, Any]] = []
    empty_batches = 0

    while len(accepted) < wanted and empty_batches < MAX_EMPTY_BATCHES:
        batch_size = min(BATCH_SIZE, wanted - len(accepted))
        prompt = _build_prompt(
            question_type, band, hsk_levels, words, items + accepted, batch_size
        )
        response = _ask(prompt)
        if response is None:
            break

        candidates = response.get("items")
        if not isinstance(candidates, list):
            empty_batches += 1
            continue

        batch_accepted = 0
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            report = content_quality.check(candidate, question_type, known)
            if not report.ok:
                print(f"  ✗ loại: {'; '.join(report.problems)}")
                continue
            key = content_quality.fingerprint(candidate, question_type)
            if key in seen:
                print("  ✗ loại: trùng câu đã có")
                continue
            seen.add(key)
            accepted.append(candidate)
            batch_accepted += 1

        print(f"  → nhận {batch_accepted}/{len(candidates)} câu (tổng {len(accepted)}/{wanted})")
        empty_batches = 0 if batch_accepted else empty_batches + 1

    for identifier, item in zip(_next_ids(items, len(accepted)), accepted):
        item["id"] = identifier
        # Recorded so a later review can tell hand-written items from generated
        # ones without digging through git history.
        item["source"] = "gemini"

    if not dry_run:
        items.extend(accepted)
    print(f"  = {len(accepted)} câu mới, pool thành {len(items)} câu")
    return accepted


# ---------------------------------------------------------------------------
# Glossing: pinyin and Vietnamese for the Chinese in an existing question
# ---------------------------------------------------------------------------

#: Which fields of each question type the review screen reads back to the
#: learner, and therefore which ones need a gloss. Mirrors ``_REVEAL_FIELDS`` in
#: :mod:`backend.services.reading_service`.
GLOSS_FIELDS: dict[str, tuple[str, ...]] = {
    "judge_true_false": ("passage_zh", "statement_zh"),
    "fill_in_blank_sentence": ("sentence_zh", "answer"),
    "multiple_choice_dialogue": ("passage_zh", "question_zh", "answer"),
    "reading_comprehension": ("passage_zh", "question_zh", "answer"),
    "sentence_reordering": ("answer",),
}

GLOSS_SYSTEM_INSTRUCTION = """\
Bạn là giáo viên tiếng Trung dạy người Việt, chuyên phiên âm và dịch.

Với mỗi đoạn chữ Hán được đưa, hãy trả về:
- "pinyin": phiên âm CÓ DẤU THANH, viết theo từ (các âm tiết của cùng một từ \
viết liền, giữa các từ có dấu cách), giữ nguyên dấu câu.
- "vi": bản dịch tiếng Việt tự nhiên, đúng nghĩa, không dịch máy móc từng chữ.

Nguyên tắc:
- Dịch sang TIẾNG VIỆT, tuyệt đối không dùng tiếng Anh.
- Giữ đúng số lượng và đúng thứ tự các mục được đưa vào.
- Với đoạn hội thoại có 男：/ 女：, giữ nguyên nhãn người nói trong bản dịch \
(Nam: / Nữ:).

CHỈ trả về JSON đúng dạng: {"items": [{"id": "...", "pinyin": "...", "vi": "..."}]}"""


def _needs_gloss(item: dict[str, Any], question_type: str) -> list[str]:
    """Fields of this item that the review screen wants but the bank lacks."""
    gloss = item.get("gloss") or {}
    missing = []
    for name in GLOSS_FIELDS.get(question_type, ()):
        entry = gloss.get(name) or {}
        if item.get(name) and not (entry.get("pinyin") and entry.get("vi")):
            missing.append(name)
    return missing


def _gloss_text(item: dict[str, Any], name: str) -> str:
    """The Chinese to gloss. Reordering answers are stored clause-separated."""
    text = str(item.get(name, ""))
    return text.replace(content_quality.ORDER_SEPARATOR, "") if name == "answer" else text


def gloss(bank: str, level: str, part: str | None, *, dry_run: bool = False) -> int:
    """Fill in pinyin and Vietnamese for questions that do not have them yet.

    Run after generating, and after any hand-written question is added: the
    review screen shown once a question has been answered reads these fields, so
    an unglossed question simply reveals less than its neighbours.
    """
    data = _load(bank)
    pools = _pools(data, bank, level)
    targets = [part] if part else list(pools)
    filled = 0

    for name in targets:
        pool = pools[name]
        question_type = pool["question_type"]
        if question_type not in GLOSS_FIELDS:
            continue  # HSKK items already ship with pinyin and vi

        # One request per field name keeps the returned list unambiguous.
        for field_name in GLOSS_FIELDS[question_type]:
            pending = [
                item for item in pool["items"] if field_name in _needs_gloss(item, question_type)
            ]
            if not pending:
                continue
            print(f"\n=== {pool['label']} · {field_name}: {len(pending)} câu cần phiên âm")

            for start in range(0, len(pending), BATCH_SIZE):
                chunk = pending[start : start + BATCH_SIZE]
                listing = "\n".join(
                    f'{{"id": "{item["id"]}", "text": "{_gloss_text(item, field_name)}"}}'
                    for item in chunk
                )
                response = _ask(
                    f"Phiên âm và dịch sang tiếng Việt các đoạn sau:\n{listing}",
                    system_instruction=GLOSS_SYSTEM_INSTRUCTION,
                    temperature=0.2,
                )
                if response is None:
                    break

                by_id = {str(entry.get("id")): entry for entry in response.get("items", [])}
                for item in chunk:
                    entry = by_id.get(str(item["id"]))
                    if not entry:
                        continue
                    pinyin = str(entry.get("pinyin", "")).strip()
                    vietnamese = str(entry.get("vi", "")).strip()
                    # A "pinyin" full of hanzi means the model echoed the input.
                    if not pinyin or content_quality.chinese_characters(pinyin):
                        print(f"  ✗ {item['id']}: pinyin không hợp lệ")
                        continue
                    if not vietnamese:
                        print(f"  ✗ {item['id']}: thiếu bản dịch")
                        continue
                    item.setdefault("gloss", {})[field_name] = {
                        "pinyin": pinyin,
                        "vi": vietnamese,
                    }
                    filled += 1
                print(f"  → xong {min(start + BATCH_SIZE, len(pending))}/{len(pending)}")

    if filled and not dry_run:
        _save(bank, data)
        print(f"\n✓ Đã bổ sung phiên âm/bản dịch cho {filled} mục.")
    else:
        print(f"\n{filled} mục được phiên âm (dry-run)." if dry_run else "\nKhông có gì để bổ sung.")
    return filled


def _print_inventory() -> None:
    print("Ngân hàng đề hiện tại:\n")
    for bank in BANK_FILES:
        data = _load(bank)
        print(f"[{bank}]")
        for level in data["levels"]:
            for name, pool in _pools(data, bank, level).items():
                generated = sum(1 for i in pool["items"] if i.get("source") == "gemini")
                print(
                    f"  {level:12} --part {name:3} {pool['question_type']:26} "
                    f"{len(pool['items']):4} câu ({generated} do AI sinh)"
                )
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--bank", choices=sorted(BANK_FILES), help="ngân hàng cần mở rộng")
    parser.add_argument("--level", help="beginner hoặc intermediate")
    parser.add_argument("--part", help="một phần cụ thể; bỏ trống để làm mọi phần")
    parser.add_argument("--count", type=int, default=20, help="số câu mới mỗi phần")
    parser.add_argument("--dry-run", action="store_true", help="chỉ kiểm thử, không ghi file")
    parser.add_argument("--list", action="store_true", help="xem quy mô ngân hàng đề")
    parser.add_argument(
        "--gloss",
        action="store_true",
        help="không sinh câu mới, chỉ bổ sung pinyin và bản dịch cho câu đã có",
    )
    arguments = parser.parse_args()

    if arguments.list:
        _print_inventory()
        return
    if not arguments.bank or not arguments.level:
        parser.error("cần --bank và --level (hoặc dùng --list)")
    if not gemini_service.is_configured():
        raise SystemExit(
            "Chưa có GEMINI_API_KEY. Đặt biến môi trường rồi chạy lại — "
            "khoá chỉ đọc từ môi trường, không lưu vào repo."
        )

    if arguments.gloss:
        gloss(arguments.bank, arguments.level, arguments.part, dry_run=arguments.dry_run)
        return

    generate(
        arguments.bank,
        arguments.level,
        arguments.part,
        arguments.count,
        dry_run=arguments.dry_run,
    )


if __name__ == "__main__":
    main()
