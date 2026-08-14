"""Matching game session and attempt handling."""

from __future__ import annotations

import random
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import session_store
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.session_store import SessionKind
from backend.services.vocabulary_service import get_random_vocabulary


SESSION = SessionKind(
    table="study_sessions",
    not_found="Không tìm thấy phiên học.",
    already_ended="Phiên học này đã kết thúc.",
    completed="Đã hoàn tất vòng nối từ.",
    type_column="session_type",
    type_value="matching",
)


def _shuffle_different(items: list[dict[str, Any]], original_ids: list[int]) -> None:
    """Shuffle, then guarantee the two columns are not already lined up."""
    random.shuffle(items)
    if len(items) > 1 and [item["vocabulary_id"] for item in items] == original_ids:
        items.append(items.pop(0))


def create_session(mode: str, count: int) -> dict[str, Any]:
    vocabulary = get_random_vocabulary(count)
    if len(vocabulary) < 2:
        raise InvalidOperationError("Không đủ từ để tạo vòng nối từ.")
    session_id = session_store.start(SESSION, total_items=len(vocabulary))

    left_items = [
        {"vocabulary_id": item["id"], "text": item["hanzi"]} for item in vocabulary
    ]
    right_field = "meaning" if mode == "meaning" else "pinyin"
    right_items = [
        {"vocabulary_id": item["id"], "text": item[right_field]} for item in vocabulary
    ]
    random.shuffle(left_items)
    _shuffle_different(right_items, [item["vocabulary_id"] for item in left_items])
    return {
        "session_id": session_id,
        "mode": mode,
        "left_items": left_items,
        "right_items": right_items,
    }


def record_attempt(
    session_id: int,
    vocabulary_id: int,
    mode: str,
    is_correct: bool,
) -> dict[str, Any]:
    with get_connection() as connection:
        session_store.require_open(connection, SESSION, session_id)
        exists = connection.execute(
            "SELECT 1 FROM vocabulary WHERE id = ?", (vocabulary_id,)
        ).fetchone()
        if not exists:
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")
        connection.execute(
            """
            INSERT INTO matching_attempts (
                session_id, vocabulary_id, matching_mode, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, vocabulary_id, mode, int(is_correct), utc_now()),
        )
    return {
        "message": "Đã ghi nhận lần nối.",
        "session_id": session_id,
        "vocabulary_id": vocabulary_id,
        "is_correct": is_correct,
    }


def complete_session(
    session_id: int,
    total_items: int,
    correct_items: int,
    incorrect_items: int,
) -> dict[str, Any]:
    return session_store.complete(
        SESSION, session_id, total_items, correct_items, incorrect_items
    )
