"""Flashcard sessions and review rules."""

from __future__ import annotations

from typing import Any

from backend.database import get_connection, utc_now
from backend.services import session_store
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.session_store import SessionKind
from backend.services.vocabulary_service import get_random_vocabulary


# Flashcard and Nối từ share the original `study_sessions` table and are told
# apart by `session_type`, so both kinds carry the discriminator.
SESSION = SessionKind(
    table="study_sessions",
    not_found="Không tìm thấy phiên học.",
    already_ended="Phiên học này đã kết thúc.",
    completed="Đã hoàn tất phiên thẻ ghi nhớ.",
    type_column="session_type",
    type_value="flashcard",
)


def create_session(
    count: int,
    include_mastered: bool,
    hsk_level: str | None = None,
) -> dict[str, Any]:
    items = get_random_vocabulary(
        count, include_mastered=include_mastered, hsk_level=hsk_level
    )
    if not items:
        raise InvalidOperationError("Không có từ phù hợp để tạo phiên thẻ ghi nhớ.")
    session_id = session_store.start(SESSION, total_items=len(items))
    # hsk_level is part of the payload because the card shows it as a badge;
    # without it the badge rendered "HSK undefined".
    fields = (
        "id", "hanzi", "pinyin", "meaning", "example",
        "example_pinyin", "example_meaning", "topic", "status", "hsk_level",
    )
    return {
        "session_id": session_id,
        "items": [{field: item[field] for field in fields} for item in items],
    }


def review_card(session_id: int, vocabulary_id: int, result: str) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        session_store.require_open(connection, SESSION, session_id)
        vocabulary = connection.execute(
            "SELECT id FROM vocabulary WHERE id = ?", (vocabulary_id,)
        ).fetchone()
        if not vocabulary:
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")
        current = connection.execute(
            "SELECT * FROM learning_progress WHERE vocabulary_id = ?", (vocabulary_id,)
        ).fetchone()
        correct_count = current["correct_count"] if current else 0

        if result == "forgot":
            status = "review"
            correct_increment = 0
            incorrect_increment = 1
        elif result == "hard":
            status = "learning"
            correct_increment = 0
            incorrect_increment = 0
        else:
            correct_increment = 1
            incorrect_increment = 0
            status = "mastered" if correct_count + 1 >= 3 else "learning"

        connection.execute(
            """
            INSERT INTO learning_progress (
                vocabulary_id, status, review_count, correct_count,
                incorrect_count, last_reviewed_at, created_at, updated_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(vocabulary_id) DO UPDATE SET
                status = excluded.status,
                review_count = learning_progress.review_count + 1,
                correct_count = learning_progress.correct_count + excluded.correct_count,
                incorrect_count = learning_progress.incorrect_count + excluded.incorrect_count,
                last_reviewed_at = excluded.last_reviewed_at,
                updated_at = excluded.updated_at
            """,
            (
                vocabulary_id, status, correct_increment, incorrect_increment,
                now, now, now,
            ),
        )
        progress = connection.execute(
            "SELECT * FROM learning_progress WHERE vocabulary_id = ?", (vocabulary_id,)
        ).fetchone()
    return {
        "message": "Đã lưu kết quả thẻ ghi nhớ.",
        "session_id": session_id,
        "vocabulary_id": vocabulary_id,
        "result": result,
        "progress": dict(progress),
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

