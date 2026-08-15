"""HSK mock exam: one paper that runs from written questions through to speaking.

The paper has two halves:

* a **written** section built from the multiple-choice engine in
  :mod:`backend.services.quiz_service`, graded automatically, and
* a **speaking** section following the official HSKK layout (nghe-nhắc lại,
  nghe-trả lời, nói theo đề), graded either by Gemini or by the learner.

Each half is scored out of 100 so the speaking half keeps the exam's real scale,
and the summary reports both plus their average.

Speech cannot be graded with a string comparison, so the spoken answers are sent
to Gemini with a rubric prompt (see ``_GRADING_PROMPTS``). Without a configured
key the exam still runs end to end and falls back to self-assessment.

The item bank is a static JSON file shipped with the app
(``scripts/data/hskk_bank.json``); variety comes from sampling a fresh subset of
each pool per attempt, so two sittings are never the same paper.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import (
    gemini_service,
    item_pool,
    quiz_service,
    reading_service,
    streak_service,
)
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from scripts.seed_data import FULL_DATA_DIR


BANK_FILE = "hskk_bank.json"

# The written half is a whole section, so it gets its own part number. Speaking
# parts keep the official 1/2/3 numbering from the exam paper.
WRITTEN_PART = 0
WRITTEN_MAX_SCORE = 100.0

# How much of an item's points a self-rating is worth. Deliberately generous at
# the bottom: the learner did speak, they just were not happy with it.
RATING_WEIGHTS: dict[str, float] = {
    "good": 1.0,
    "ok": 0.6,
    "bad": 0.2,
    "skipped": 0.0,
}

RATING_LABELS: dict[str, str] = {
    "good": "Trôi chảy",
    "ok": "Tạm được",
    "bad": "Còn vấp",
    "skipped": "Bỏ qua",
}


def _rating_for_percent(percent: float) -> str:
    """Bucket an AI score so the existing stats and CHECK constraint still fit."""
    if percent >= 80:
        return "good"
    if percent >= 50:
        return "ok"
    if percent > 0:
        return "bad"
    return "skipped"


# --------------------------------------------------------------------------
# Grading prompts
# --------------------------------------------------------------------------

GRADER_SYSTEM_INSTRUCTION = """\
Bạn là giám khảo kỳ thi khẩu ngữ HSKK (汉语水平口语考试) của Hanban, đã chấm thi \
nhiều năm và rất quen với lỗi phát âm của người Việt học tiếng Trung.

Bạn nhận bài làm của thí sinh — gồm bản gỡ băng (do phần nhận dạng giọng nói của \
trình duyệt ghi lại) và/hoặc đoạn ghi âm — cùng thông tin về câu hỏi. Nhiệm vụ:
1. Xác định thí sinh đã nói gì. Nếu có ghi âm thì nghe và tự gỡ lại cho chính \
xác; nếu chỉ có bản gỡ băng thì dùng nguyên văn bản đó. Không nhận được nội dung \
nào thì để transcript là chuỗi rỗng.
2. Chấm điểm theo đúng tiêu chí của phần thi được nêu trong yêu cầu.
3. Nhận xét bằng TIẾNG VIỆT, ngắn gọn, cụ thể, chỉ rõ chỗ sai và cách sửa. \
Không khen chung chung. Khi nhắc tới lỗi thanh điệu, ghi rõ chữ nào và đọc \
thành thanh mấy thay vì thanh mấy.

Nguyên tắc chấm:
- Chấm đúng thực tế, không nới tay. Nói sai nội dung thì không thể trên 50 điểm.
- Không nhận được nội dung nào thì score_percent = 0 và nói rõ là không nghe \
được thí sinh nói gì.
- KHI CHỈ CÓ BẢN GỠ BĂNG, KHÔNG CÓ GHI ÂM: máy nhận dạng giọng nói đã chuẩn hoá \
âm thanh thành chữ, nên bạn KHÔNG thể đánh giá thanh điệu hay chất giọng. Khi đó \
hãy chấm nội dung, ngữ pháp, độ đầy đủ và độ dài; đặt pronunciation_percent bằng \
mức tin cậy của việc máy nhận ra đúng chữ, và nói rõ trong nhận xét rằng phần \
phát âm chưa được chấm trực tiếp. Tuyệt đối không bịa ra lỗi thanh điệu cụ thể \
khi không nghe được âm thanh.
- Người Việt hay mắc: nhầm thanh 2 với thanh 3, bỏ mất thanh nhẹ, phát âm \
zh/ch/sh thành z/c/s, thiếu âm cuối -ng. Ưu tiên chỉ ra các lỗi này nếu có.

CHỈ trả về một đối tượng JSON đúng schema sau, không kèm giải thích nào khác:
{
  "transcript": "chuỗi chữ Hán thí sinh đã nói",
  "score_percent": số nguyên 0-100,
  "verdict": "một câu tiếng Việt tóm tắt kết quả",
  "strengths": ["điểm làm tốt, tiếng Việt, tối đa 3 mục"],
  "fixes": ["lỗi cụ thể và cách sửa, tiếng Việt, tối đa 4 mục"],
  "pronunciation_percent": số nguyên 0-100,
  "content_percent": số nguyên 0-100,
  "fluency_percent": số nguyên 0-100
}"""

# One rubric per part kind. `{...}` placeholders are filled from the paper item.
_GRADING_PROMPTS: dict[str, str] = {
    "repeat": """\
PHẦN 1 — NGHE VÀ NHẮC LẠI (听后重复).

Thí sinh vừa nghe câu sau qua loa và phải nhắc lại NGUYÊN VĂN:
- Câu gốc (chữ Hán): {hanzi}
- Phiên âm: {pinyin}
- Nghĩa tiếng Việt: {vi}

Tiêu chí chấm phần này:
- Độ khớp với câu gốc (50%): thiếu chữ, thừa chữ, sai chữ đều trừ điểm. Nhắc \
lại được toàn bộ câu mới đạt mức tối đa.
- Phát âm và thanh điệu (35%): chấm từng âm tiết, đặc biệt các chữ trong câu gốc.
- Độ trôi chảy (15%): nói liền mạch, không ngắt quãng dài, không lặp đi lặp lại.

Lưu ý: đây là bài nhắc lại, KHÔNG chấm sáng tạo nội dung. Thí sinh nói câu khác \
với câu gốc thì content_percent phải thấp dù phát âm hay.""",
    "answer": """\
PHẦN 2 — NGHE VÀ TRẢ LỜI (听后回答).

Thí sinh vừa nghe câu hỏi sau và phải trả lời bằng tiếng Trung:
- Câu hỏi (chữ Hán): {hanzi}
- Phiên âm: {pinyin}
- Nghĩa tiếng Việt: {vi}

Tiêu chí chấm phần này:
- Trả lời đúng trọng tâm câu hỏi (40%): trả lời lạc đề thì điểm nội dung phải thấp.
- Ngữ pháp và cách dùng từ (25%): đúng trật tự từ, đúng lượng từ, đúng thì/trợ từ.
- Phát âm và thanh điệu (25%).
- Độ trôi chảy và độ dài hợp lý (10%): ở trình độ này chỉ cần 1-2 câu đầy đủ, \
không cần dài. Trả lời cụt lủn kiểu một từ thì trừ điểm.""",
    "speak": """\
PHẦN 3 — NÓI THEO ĐỀ CHO SẴN (回答问题), trình độ SƠ CẤP.

Đề bài in trên giấy thi kèm phiên âm:
- Đề (chữ Hán): {hanzi}
- Phiên âm: {pinyin}
- Nghĩa tiếng Việt: {vi}
- Yêu cầu tối thiểu: {min_sentences} câu liền mạch.

Tiêu chí chấm phần này:
- Đủ số câu và bám đề (35%): đếm số câu thí sinh nói. Nói ít hơn {min_sentences} \
câu thì trừ mạnh và nêu rõ đã nói được mấy câu.
- Nội dung mạch lạc (25%): các câu liên quan tới nhau, có mở đầu và kết.
- Ngữ pháp, từ vựng ở mức HSK 1-2 (20%).
- Phát âm, thanh điệu và độ trôi chảy (20%).

Ở trình độ sơ cấp KHÔNG đòi hỏi lập luận phức tạp; câu đơn giản nhưng đúng và \
đủ ý vẫn được điểm cao.""",
    "opinion": """\
PHẦN 3 — NÊU QUAN ĐIỂM (回答问题), trình độ TRUNG CẤP.

Câu hỏi thảo luận:
- Đề (chữ Hán): {hanzi}
- Phiên âm: {pinyin}
- Nghĩa tiếng Việt: {vi}

Tiêu chí chấm phần này:
- Nêu rõ quan điểm và bảo vệ được quan điểm đó (30%): phải có ý kiến rõ ràng, \
kèm ít nhất một lý do và một ví dụ minh hoạ.
- Bố cục mở - thân - kết (20%): có dùng các cấu trúc như 首先…然后…最后…, \
第一…第二…, 我认为…, 总的来说… thì cộng điểm.
- Ngữ pháp và từ vựng mức HSK 3-4 (20%): khuyến khích liên từ và mệnh đề phụ \
(虽然…但是…, 不但…而且…, 如果…就…).
- Phát âm, thanh điệu (15%).
- Độ dài và độ trôi chảy (15%): mức mong đợi là nói liên tục khoảng 1-2 phút. \
Nói dưới 30 giây thì trừ điểm và nêu rõ.""",
    "describe": """\
PHẦN 2 — KỂ LẠI TÌNH HUỐNG (看图说话), trình độ TRUNG CẤP.

Tình huống cho sẵn:
- Chủ đề (chữ Hán): {hanzi}
- Phiên âm: {pinyin}
- Mô tả tình huống: {vi}

Tiêu chí chấm phần này:
- Kể đúng tình huống được giao (30%).
- Bố cục mở - thân - kết rõ ràng (25%): dùng 首先…然后…最后… hoặc 第一…第二…第三…
- Ngữ pháp và từ vựng mức HSK 3-4 (25%).
- Phát âm, thanh điệu và độ trôi chảy (20%).""",
}


@lru_cache(maxsize=1)
def _load_bank() -> dict[str, Any]:
    path = FULL_DATA_DIR / BANK_FILE
    if not path.is_file():
        raise InvalidOperationError("Không tìm thấy ngân hàng đề HSKK.")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _get_level(exam_level: str) -> dict[str, Any]:
    level = _load_bank()["levels"].get(exam_level)
    if not level:
        raise ResourceNotFoundError("Không có cấp độ HSKK này.")
    return level


def _part_config(exam_level: str, part: int) -> dict[str, Any]:
    level = _get_level(exam_level)
    if part == WRITTEN_PART:
        reading = reading_service.describe(exam_level)
        return {
            "part": WRITTEN_PART,
            "kind": "reading",
            "title": reading["section_name_vi"],
            "points_per_item": round(WRITTEN_MAX_SCORE / reading["total_questions"], 4),
            "count": reading["total_questions"],
        }
    for config in level["parts"]:
        if config["part"] == part:
            return config
    raise ResourceNotFoundError("Đề thi không có phần này.")


def list_levels() -> dict[str, Any]:
    """Format summary for the intro screen — no items, so it is cheap to poll."""
    items = []
    for code, level in _load_bank()["levels"].items():
        parts = [
            {
                "part": part["part"],
                "kind": part["kind"],
                "title": part["title"],
                "instruction_zh": part["instruction_zh"],
                "instruction_vi": part["instruction_vi"],
                "count": part["count"],
                "points_per_item": part["points_per_item"],
                "total_points": round(part["count"] * part["points_per_item"], 1),
                "answer_seconds": part["answer_seconds"],
            }
            for part in level["parts"]
        ]
        reading = reading_service.describe(code)
        items.append(
            {
                "code": code,
                "label": level["label"],
                "hsk_range": level["hsk_range"],
                "blurb": level["blurb"],
                "prep_seconds": level["prep_seconds"],
                "pass_score": level["pass_score"],
                "reading": {**reading, "total_points": WRITTEN_MAX_SCORE},
                "speaking_items": sum(part["count"] for part in level["parts"]),
                "total_items": reading["total_questions"]
                + sum(part["count"] for part in level["parts"]),
                "speaking_points": round(sum(part["total_points"] for part in parts), 1),
                "parts": parts,
                # Surfaced so the UI can explain the gap instead of quietly
                # shipping a paper that does not match the official format.
                "skipped_parts": level.get("skipped_parts", []),
                "ai_grading": gemini_service.is_configured(),
            }
        )
    return {"items": items}


def list_pools(exam_level: str) -> list[dict[str, Any]]:
    """The speaking pools behind one exam level, for the bank inventory."""
    level = _get_level(exam_level)
    return [
        {
            "label": part["title"],
            "question_type": part["kind"],
            "draw_per_exam": part["count"],
            "items": level["pools"][str(part["part"])],
        }
        for part in level["parts"]
    ]


def list_exam_levels() -> list[dict[str, str]]:
    """Code, label and HSK range of each exam band, without loading any items."""
    return [
        {"code": code, "label": level["label"], "hsk_range": level["hsk_range"]}
        for code, level in _load_bank()["levels"].items()
    ]


def _build_speaking_parts(level: dict[str, Any]) -> list[dict[str, Any]]:
    parts = []
    for config in level["parts"]:
        pool = level["pools"][str(config["part"])]
        chosen = item_pool.take(pool, config["count"])
        parts.append(
            {
                "part": config["part"],
                "kind": config["kind"],
                "title": config["title"],
                "instruction_zh": config["instruction_zh"],
                "instruction_vi": config["instruction_vi"],
                "points_per_item": config["points_per_item"],
                "answer_seconds": config["answer_seconds"],
                "min_sentences": config.get("min_sentences"),
                "items": [
                    {
                        "question_index": index,
                        "question_id": item["id"],
                        "hanzi": item["hanzi"],
                        "pinyin": item["pinyin"],
                        "vi": item["vi"],
                        "hints": item.get("hints", []),
                        # Parts 1 and 2 are heard, never read: the runner must not
                        # show the text before the learner has answered.
                        "audio_text": item["hanzi"] if config["kind"] in {"repeat", "answer"} else None,
                    }
                    for index, item in enumerate(chosen)
                ],
            }
        )
    return parts


def create_session(exam_level: str) -> dict[str, Any]:
    level = _get_level(exam_level)
    parts = _build_speaking_parts(level)

    # The reading half follows the real 阅读 section and keeps its answer key on
    # the server; it still books a quiz session so the existing quiz statistics
    # and achievements keep counting the results.
    reading = reading_service.build_section(exam_level)
    reading_count = reading["total_questions"]
    quiz_session = quiz_service.create_session(
        None, level["written"]["question_types"], reading_count
    )

    speaking_items = sum(len(part["items"]) for part in parts)
    speaking_max = round(
        sum(len(part["items"]) * part["points_per_item"] for part in parts), 1
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO hskk_sessions (
                exam_level, started_at, total_items, max_score,
                quiz_session_id, written_max
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                exam_level,
                utc_now(),
                speaking_items + reading_count,
                speaking_max,
                quiz_session["session_id"],
                WRITTEN_MAX_SCORE,
            ),
        )
        session_id = cursor.lastrowid

    reading["part"] = WRITTEN_PART
    reading["points_per_item"] = round(WRITTEN_MAX_SCORE / reading_count, 4)
    reading["max_score"] = WRITTEN_MAX_SCORE

    return {
        "session_id": session_id,
        "quiz_session_id": quiz_session["session_id"],
        "exam_level": exam_level,
        "label": level["label"],
        "prep_seconds": level["prep_seconds"],
        "pass_score": level["pass_score"],
        "total_items": speaking_items + reading_count,
        "max_score": speaking_max,
        "ai_grading": gemini_service.is_configured(),
        "reading": reading,
        "parts": parts,
    }


def _get_open_session(connection: Any, session_id: int) -> Any:
    session = connection.execute(
        "SELECT * FROM hskk_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        raise ResourceNotFoundError("Không tìm thấy bài thi thử.")
    if session["ended_at"]:
        raise InvalidOperationError("Bài thi thử này đã nộp.")
    return session


def _store_answer(
    connection: Any,
    session_id: int,
    part: int,
    question_index: int,
    question_id: str,
    self_rating: str,
    score: float,
    max_score: float,
    spoken_seconds: int,
    graded_by: str,
    ai_score: float | None = None,
    ai_feedback: str | None = None,
    transcript: str | None = None,
    given_answer: str = "",
) -> None:
    connection.execute(
        """
        INSERT INTO hskk_answers (
            session_id, part, question_index, question_id, self_rating,
            score, max_score, spoken_seconds, created_at,
            graded_by, ai_score, ai_feedback, transcript, given_answer
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (session_id, part, question_index) DO UPDATE SET
            question_id = excluded.question_id,
            self_rating = excluded.self_rating,
            score = excluded.score,
            max_score = excluded.max_score,
            spoken_seconds = excluded.spoken_seconds,
            created_at = excluded.created_at,
            graded_by = excluded.graded_by,
            ai_score = excluded.ai_score,
            ai_feedback = excluded.ai_feedback,
            transcript = excluded.transcript,
            given_answer = excluded.given_answer
        """,
        (
            session_id,
            part,
            question_index,
            question_id,
            self_rating,
            round(score, 2),
            round(max_score, 4),
            spoken_seconds,
            utc_now(),
            graded_by,
            ai_score,
            ai_feedback,
            transcript,
            given_answer,
        ),
    )


def record_reading_answer(
    session_id: int, question_index: int, question_id: str, answer: Any
) -> dict[str, Any]:
    """Grade one reading question. The client sends what was picked, not whether
    it was right — the answer key stays on this side of the wire."""
    with get_connection() as connection:
        session = _get_open_session(connection, session_id)
        exam_level = session["exam_level"]

    outcome = reading_service.check_answer(exam_level, question_id, answer)
    is_correct = outcome["is_correct"]

    with get_connection() as connection:
        _get_open_session(connection, session_id)
        config = _part_config(exam_level, WRITTEN_PART)
        max_score = float(config["points_per_item"])
        score = max_score if is_correct else 0.0
        _store_answer(
            connection,
            session_id,
            WRITTEN_PART,
            question_index,
            question_id,
            "good" if is_correct else "bad",
            score,
            max_score,
            0,
            "auto",
        )

    return {
        "session_id": session_id,
        "question_index": question_index,
        "score": round(score, 2),
        "max_score": round(max_score, 4),
        **outcome,
    }


def record_answer(
    session_id: int,
    part: int,
    question_index: int,
    question_id: str,
    self_rating: str,
    spoken_seconds: int,
) -> dict[str, Any]:
    """Record a spoken answer the learner graded themselves."""
    with get_connection() as connection:
        session = _get_open_session(connection, session_id)
        config = _part_config(session["exam_level"], part)
        max_score = float(config["points_per_item"])
        score = round(max_score * RATING_WEIGHTS[self_rating], 2)
        _store_answer(
            connection,
            session_id,
            part,
            question_index,
            question_id,
            self_rating,
            score,
            max_score,
            spoken_seconds,
            "self",
        )
    return {
        "session_id": session_id,
        "part": part,
        "question_index": question_index,
        "self_rating": self_rating,
        "score": score,
        "max_score": max_score,
    }


def _find_item(exam_level: str, part: int, question_id: str) -> dict[str, Any]:
    pool = _get_level(exam_level)["pools"].get(str(part), [])
    for item in pool:
        if item["id"] == question_id:
            return item
    raise ResourceNotFoundError("Không tìm thấy câu hỏi này trong ngân hàng đề.")


def _clamp_percent(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _clean_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(entry).strip() for entry in value[:limit] if str(entry).strip()]


def build_grading_prompt(
    exam_level: str,
    part: int,
    question_id: str,
    transcript: str,
    spoken_seconds: int,
    has_audio: bool,
) -> str:
    """Assemble the rubric, the question and the learner's answer into a prompt.

    Kept public and side-effect free so the exact text sent to Gemini can be
    asserted in tests rather than only observed through a live call.
    """
    config = _part_config(exam_level, part)
    item = _find_item(exam_level, part, question_id)

    template = _GRADING_PROMPTS.get(config["kind"])
    if not template:
        raise InvalidOperationError("Phần thi này không chấm bằng AI được.")

    prompt = template.format(
        hanzi=item["hanzi"],
        pinyin=item["pinyin"],
        vi=item["vi"],
        min_sentences=config.get("min_sentences") or 5,
    )

    prompt += f"\n\nBÀI LÀM CỦA THÍ SINH (nói trong {spoken_seconds} giây):\n"
    if transcript:
        prompt += f'Bản gỡ băng do trình duyệt ghi lại: "{transcript}"\n'
    else:
        prompt += "Phần nhận dạng giọng nói không ghi được chữ nào.\n"
    if has_audio:
        prompt += "Đoạn ghi âm gốc được gửi kèm ngay sau đây — hãy nghe để chấm phát âm và thanh điệu."
    else:
        prompt += (
            "KHÔNG có file ghi âm kèm theo, chỉ có bản gỡ băng ở trên. "
            "Đừng chấm thanh điệu như thể đã nghe được giọng thí sinh."
        )
    return prompt


def grade_answer(
    session_id: int,
    part: int,
    question_index: int,
    question_id: str,
    transcript: str,
    audio_base64: str | None,
    audio_mime_type: str,
    spoken_seconds: int,
) -> dict[str, Any]:
    """Send one spoken answer to Gemini and store the score it comes back with."""
    transcript = (transcript or "").strip()
    if not transcript and not audio_base64:
        raise InvalidOperationError(
            "Chưa có nội dung nào để chấm. Hãy ghi âm lại và nói to, rõ hơn."
        )

    with get_connection() as connection:
        session = _get_open_session(connection, session_id)
        exam_level = session["exam_level"]
    config = _part_config(exam_level, part)
    item = _find_item(exam_level, part, question_id)

    prompt = build_grading_prompt(
        exam_level, part, question_id, transcript, spoken_seconds, bool(audio_base64)
    )

    result = gemini_service.generate_json(
        system_instruction=GRADER_SYSTEM_INSTRUCTION,
        prompt=prompt,
        audio_base64=audio_base64,
        audio_mime_type=audio_mime_type,
    )

    percent = _clamp_percent(result.get("score_percent"))
    max_score = float(config["points_per_item"])
    score = round(max_score * percent / 100, 2)
    verdict = str(result.get("verdict", "")).strip()
    strengths = _clean_list(result.get("strengths"), 3)
    fixes = _clean_list(result.get("fixes"), 4)
    # Prefer the model's own transcription when it had the audio to work from;
    # otherwise keep what the browser heard.
    transcript = str(result.get("transcript", "")).strip() or transcript

    feedback = {
        "verdict": verdict,
        "strengths": strengths,
        "fixes": fixes,
        "pronunciation_percent": _clamp_percent(result.get("pronunciation_percent")),
        "content_percent": _clamp_percent(result.get("content_percent")),
        "fluency_percent": _clamp_percent(result.get("fluency_percent")),
    }

    with get_connection() as connection:
        _get_open_session(connection, session_id)
        _store_answer(
            connection,
            session_id,
            part,
            question_index,
            question_id,
            _rating_for_percent(percent),
            score,
            max_score,
            spoken_seconds,
            "ai",
            ai_score=percent,
            ai_feedback=json.dumps(feedback, ensure_ascii=False),
            transcript=transcript,
        )

    return {
        "session_id": session_id,
        "part": part,
        "question_index": question_index,
        "score": score,
        "max_score": max_score,
        "percent": percent,
        "transcript": transcript,
        "expected": item["hanzi"],
        "graded_by": "ai",
        **feedback,
    }


def _band(percent: float) -> str:
    if percent >= 85:
        return "Rất tốt — sẵn sàng thi thật"
    if percent >= 70:
        return "Khá — cần gọt lại phát âm và độ trôi chảy"
    if percent >= 60:
        return "Vừa đủ đỗ — nên luyện thêm phần nói dài"
    return "Chưa đạt — tập trung vào phần nhắc lại trước"


def complete_session(session_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        session = _get_open_session(connection, session_id)
        rows = connection.execute(
            """
            SELECT part,
                   COUNT(*) AS answered,
                   COALESCE(SUM(score), 0) AS score,
                   COALESCE(SUM(max_score), 0) AS max_score,
                   COALESCE(SUM(spoken_seconds), 0) AS spoken_seconds
            FROM hskk_answers
            WHERE session_id = ?
            GROUP BY part
            ORDER BY part
            """,
            (session_id,),
        ).fetchall()

        written_row = next((row for row in rows if row["part"] == WRITTEN_PART), None)
        speaking_rows = [row for row in rows if row["part"] != WRITTEN_PART]

        answered = sum(row["answered"] for row in rows)
        written_score = round(written_row["score"], 1) if written_row else 0.0
        speaking_score = round(sum(row["score"] for row in speaking_rows), 1)
        speaking_max = float(session["max_score"]) or 100.0
        written_max = float(session["written_max"]) or WRITTEN_MAX_SCORE

        connection.execute(
            """
            UPDATE hskk_sessions
            SET ended_at = ?, answered_items = ?, score = ?, written_score = ?
            WHERE id = ?
            """,
            (utc_now(), answered, speaking_score, written_score, session_id),
        )

        parts = [
            {
                "part": row["part"],
                "title": _part_config(session["exam_level"], row["part"])["title"],
                "answered": row["answered"],
                "score": round(row["score"], 1),
                "max_score": round(row["max_score"], 1),
                "spoken_seconds": row["spoken_seconds"],
            }
            for row in rows
        ]
        exam_level = session["exam_level"]
        total_items = session["total_items"]
        quiz_session_id = session["quiz_session_id"]

    speaking_percent = round(speaking_score / speaking_max * 100, 1) if speaking_max else 0.0
    written_percent = round(written_score / written_max * 100, 1) if written_max else 0.0
    # Both halves weigh the same: the written section shows whether the words are
    # known, the speaking section whether they can be used.
    overall = round((speaking_percent + written_percent) / 2, 1)
    pass_score = _get_level(exam_level)["pass_score"]

    with get_connection() as connection:
        counts = connection.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END), 0) AS correct,
                   COALESCE(SUM(CASE WHEN score = 0 THEN 1 ELSE 0 END), 0) AS incorrect
            FROM hskk_answers WHERE session_id = ? AND part = ?
            """,
            (session_id, WRITTEN_PART),
        ).fetchone()
        correct_written = counts["correct"] or 0
        incorrect_written = counts["incorrect"] or 0

    if quiz_session_id:
        try:
            quiz_service.complete_session(
                quiz_session_id,
                correct_written + incorrect_written,
                correct_written,
                incorrect_written,
            )
        except (InvalidOperationError, ResourceNotFoundError):
            # The quiz half is bookkeeping; never let it block submitting the exam.
            streak_service.record_session_result(correct_written, incorrect_written)

    return {
        "session_id": session_id,
        "exam_level": exam_level,
        "score": speaking_score,
        "max_score": round(speaking_max, 1),
        "percent": speaking_percent,
        "written_score": written_score,
        "written_max": round(written_max, 1),
        "written_percent": written_percent,
        "overall_percent": overall,
        "passed": overall >= pass_score,
        "pass_score": pass_score,
        "band": _band(overall),
        "total_items": total_items,
        "answered_items": answered,
        "parts": parts,
    }


def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT exam_level, score, max_score, written_score, written_max,
                   started_at, ended_at
            FROM hskk_sessions
            WHERE ended_at IS NOT NULL
            ORDER BY started_at DESC
            """
        ).fetchall()
        ratings = connection.execute(
            """
            SELECT self_rating, COUNT(*) AS total
            FROM hskk_answers
            WHERE part != ?
            GROUP BY self_rating
            """,
            (WRITTEN_PART,),
        ).fetchall()

    def overall_of(row: Any) -> float:
        speaking = row["score"] / (row["max_score"] or 100) * 100
        written = row["written_score"] / (row["written_max"] or 100) * 100
        return (speaking + written) / 2

    scores = [overall_of(row) for row in rows]
    return {
        "sessions": len(rows),
        "best_percent": round(max(scores), 1) if scores else 0,
        "average_percent": round(sum(scores) / len(scores), 1) if scores else 0,
        "last_percent": round(scores[0], 1) if scores else 0,
        "ai_grading": gemini_service.is_configured(),
        "recent": [
            {
                "exam_level": row["exam_level"],
                "score": round(row["score"], 1),
                "max_score": round(row["max_score"], 1),
                "percent": round(overall_of(row), 1),
                "written_percent": round(
                    row["written_score"] / (row["written_max"] or 100) * 100, 1
                ),
                "ended_at": row["ended_at"],
            }
            for row in rows[:10]
        ],
        "ratings": [
            {
                "self_rating": row["self_rating"],
                "label": RATING_LABELS.get(row["self_rating"], row["self_rating"]),
                "total": row["total"],
            }
            for row in ratings
        ],
    }
