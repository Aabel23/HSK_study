"""Listening practice: hear a word spoken, pick the correct meaning or hanzi."""

from __future__ import annotations

import random
from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.vocabulary_service import get_random_vocabulary


OPTION_COUNT = 4
LABEL_FIELD_BY_MODE = {
    "audio_to_meaning": "meaning",
    "audio_to_hanzi": "hanzi",
}


def _generate_one(hsk_level: str | None, mode: str) -> dict[str, Any]:
    targets = get_random_vocabulary(1, hsk_level=hsk_level)
    if not targets:
        raise InvalidOperationError("Không có từ phù hợp để tạo bài nghe.")
    target = targets[0]

    distractors = get_random_vocabulary(
        OPTION_COUNT - 1, hsk_level=hsk_level, exclude_ids=[target["id"]]
    )
    if len(distractors) < OPTION_COUNT - 1:
        distractors = get_random_vocabulary(OPTION_COUNT - 1, exclude_ids=[target["id"]])
    if len(distractors) < OPTION_COUNT - 1:
        raise InvalidOperationError("Không đủ từ vựng để tạo các lựa chọn.")

    label_field = LABEL_FIELD_BY_MODE[mode]
    options = [{"vocabulary_id": target["id"], "label": target[label_field]}]
    options.extend({"vocabulary_id": d["id"], "label": d[label_field]} for d in distractors)
    random.shuffle(options)

    return {
        "mode": mode,
        "target_vocabulary_id": target["id"],
        "audio_text": target["hanzi"],
        "options": options,
    }


def create_session(hsk_level: str | None, mode: str, count: int) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO listening_sessions (hsk_level, mode, started_at, total_items)
            VALUES (?, ?, ?, ?)
            """,
            (hsk_level or "all", mode, now, count),
        )
        session_id = cursor.lastrowid

    items = []
    for index in range(count):
        item = _generate_one(hsk_level, mode)
        item["item_id"] = index
        items.append(item)

    return {"session_id": session_id, "hsk_level": hsk_level or "all", "mode": mode, "items": items}


def _get_open_session(connection: Any, session_id: int) -> Any:
    session = connection.execute(
        "SELECT * FROM listening_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        raise ResourceNotFoundError("Không tìm thấy phiên luyện nghe.")
    if session["ended_at"]:
        raise InvalidOperationError("Phiên luyện nghe này đã kết thúc.")
    return session


def record_attempt(
    session_id: int, vocabulary_id: int, mode: str, is_correct: bool
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
            INSERT INTO listening_attempts (
                session_id, vocabulary_id, mode, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, vocabulary_id, mode, int(is_correct), now),
        )
    return {
        "message": "Đã ghi nhận lần nghe.",
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
            UPDATE listening_sessions
            SET ended_at = ?, total_items = ?, correct_items = ?, incorrect_items = ?
            WHERE id = ?
            """,
            (now, total_items, correct_items, incorrect_items, session_id),
        )
    return {"message": "Đã hoàn tất bài luyện nghe.", "session_id": session_id}


def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(DISTINCT s.id) AS sessions,
                   COALESCE(SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END), 0) AS correct,
                   COALESCE(SUM(CASE WHEN a.is_correct = 0 THEN 1 ELSE 0 END), 0) AS incorrect
            FROM listening_sessions s
            LEFT JOIN listening_attempts a ON a.session_id = s.id
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
