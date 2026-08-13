"""Multiple-choice quiz/test sessions built from the vocabulary bank."""

from __future__ import annotations

import json
import random
from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.vocabulary_service import get_random_vocabulary
from backend.services import streak_service


DEFAULT_QUESTION_TYPES = ["mcq_meaning", "mcq_hanzi", "mcq_pinyin", "mcq_audio"]
OPTION_COUNT = 4

LABEL_FIELD_BY_TYPE = {
    "mcq_meaning": "meaning",
    "mcq_hanzi": "hanzi",
    "mcq_pinyin": "pinyin",
    "mcq_audio": "meaning",
}


def _build_prompt(question_type: str, target: dict[str, Any]) -> dict[str, Any]:
    if question_type == "mcq_meaning":
        return {"hanzi": target["hanzi"], "pinyin": target["pinyin"]}
    if question_type == "mcq_hanzi":
        return {"meaning": target["meaning"]}
    if question_type == "mcq_pinyin":
        return {"hanzi": target["hanzi"]}
    if question_type == "mcq_audio":
        return {"audio_text": target["hanzi"]}
    raise InvalidOperationError("Loại câu hỏi không hợp lệ.")


def _generate_one(hsk_level: str | None, question_type: str) -> dict[str, Any]:
    targets = get_random_vocabulary(1, hsk_level=hsk_level)
    if not targets:
        raise InvalidOperationError("Không có từ phù hợp để tạo câu hỏi.")
    target = targets[0]

    distractors = get_random_vocabulary(
        OPTION_COUNT - 1, hsk_level=hsk_level, exclude_ids=[target["id"]]
    )
    if len(distractors) < OPTION_COUNT - 1:
        distractors = get_random_vocabulary(OPTION_COUNT - 1, exclude_ids=[target["id"]])
    if len(distractors) < OPTION_COUNT - 1:
        raise InvalidOperationError("Không đủ từ vựng để tạo các lựa chọn.")

    label_field = LABEL_FIELD_BY_TYPE[question_type]
    options = [{"vocabulary_id": target["id"], "label": target[label_field]}]
    options.extend({"vocabulary_id": d["id"], "label": d[label_field]} for d in distractors)
    random.shuffle(options)

    return {
        "question_type": question_type,
        "target_vocabulary_id": target["id"],
        "prompt": _build_prompt(question_type, target),
        "options": options,
    }


def generate_questions(
    hsk_levels: list[str] | None, question_types: list[str], count: int
) -> list[dict[str, Any]]:
    """Build a mixed batch of multiple-choice questions.

    Unlike :func:`create_session` this takes *several* HSK levels and picks one
    per question, which is what the HSK mock exam needs — a paper covers a band
    (HSK 1-2, HSK 3-4) rather than a single level. No session row is written, so
    the caller owns the bookkeeping.
    """
    active_types = question_types or list(DEFAULT_QUESTION_TYPES)
    questions = []
    for index in range(count):
        level = random.choice(hsk_levels) if hsk_levels else None
        question = _generate_one(level, random.choice(active_types))
        question["question_id"] = index
        questions.append(question)
    return questions


def create_session(
    hsk_level: str | None, question_types: list[str], count: int
) -> dict[str, Any]:
    active_types = question_types or list(DEFAULT_QUESTION_TYPES)
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO quiz_sessions (hsk_level, question_types_json, started_at, total_items)
            VALUES (?, ?, ?, ?)
            """,
            (hsk_level or "all", json.dumps(active_types), now, count),
        )
        session_id = cursor.lastrowid

    questions = []
    for index in range(count):
        question = _generate_one(hsk_level, random.choice(active_types))
        question["question_id"] = index
        questions.append(question)

    return {"session_id": session_id, "hsk_level": hsk_level or "all", "questions": questions}


def _get_open_session(connection: Any, session_id: int) -> Any:
    session = connection.execute(
        "SELECT * FROM quiz_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        raise ResourceNotFoundError("Không tìm thấy phiên kiểm tra.")
    if session["ended_at"]:
        raise InvalidOperationError("Phiên kiểm tra này đã kết thúc.")
    return session


def record_attempt(
    session_id: int, vocabulary_id: int, question_type: str, is_correct: bool
) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        _get_open_session(connection, session_id)
        exists = connection.execute(
            "SELECT 1 FROM vocabulary WHERE id = ?", (vocabulary_id,)
        ).fetchone()
        if not exists:
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")
        connection.execute(
            """
            INSERT INTO quiz_attempts (
                session_id, vocabulary_id, question_type, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, vocabulary_id, question_type, int(is_correct), now),
        )
    return {
        "message": "Đã ghi nhận câu trả lời.",
        "session_id": session_id,
        "vocabulary_id": vocabulary_id,
        "is_correct": is_correct,
    }


def complete_session(
    session_id: int, total_items: int, correct_items: int, incorrect_items: int
) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        _get_open_session(connection, session_id)
        connection.execute(
            """
            UPDATE quiz_sessions
            SET ended_at = ?, total_items = ?, correct_items = ?, incorrect_items = ?
            WHERE id = ?
            """,
            (now, total_items, correct_items, incorrect_items, session_id),
        )
    streak_service.record_session_result(correct_items, incorrect_items)
    return {"message": "Đã hoàn tất bài kiểm tra.", "session_id": session_id}


def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(DISTINCT s.id) AS sessions,
                   COALESCE(SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END), 0) AS correct,
                   COALESCE(SUM(CASE WHEN a.is_correct = 0 THEN 1 ELSE 0 END), 0) AS incorrect
            FROM quiz_sessions s
            LEFT JOIN quiz_attempts a ON a.session_id = s.id
            """
        ).fetchone()
    correct = row["correct"] or 0
    incorrect = row["incorrect"] or 0
    total = correct + incorrect
    return {
        "sessions": row["sessions"] or 0,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": round(correct / total * 100, 1) if total else 0,
    }
