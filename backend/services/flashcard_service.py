"""Flashcard sessions and review rules."""

from __future__ import annotations

from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.vocabulary_service import get_random_vocabulary
from backend.services import streak_service


def create_session(count: int, include_mastered: bool) -> dict[str, Any]:
    items = get_random_vocabulary(count, include_mastered=include_mastered)
    if not items:
        raise InvalidOperationError("Không có từ phù hợp để tạo phiên Flashcard.")
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO study_sessions (session_type, started_at, total_items) VALUES ('flashcard', ?, ?)",
            (now, len(items)),
        )
        session_id = cursor.lastrowid
    fields = (
        "id", "hanzi", "pinyin", "meaning", "example",
        "example_pinyin", "example_meaning", "topic", "status",
    )
    return {
        "session_id": session_id,
        "items": [{field: item[field] for field in fields} for item in items],
    }


def _validate_session(connection: Any, session_id: int, expected_type: str) -> Any:
    session = connection.execute(
        "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        raise ResourceNotFoundError("Không tìm thấy phiên học.")
    if session["session_type"] != expected_type:
        raise InvalidOperationError("Loại phiên học không hợp lệ cho thao tác này.")
    if session["ended_at"]:
        raise InvalidOperationError("Phiên học này đã kết thúc.")
    return session


def review_card(session_id: int, vocabulary_id: int, result: str) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        _validate_session(connection, session_id, "flashcard")
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
        "message": "Đã lưu kết quả Flashcard.",
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
    now = utc_now()
    with get_connection() as connection:
        _validate_session(connection, session_id, "flashcard")
        connection.execute(
            """
            UPDATE study_sessions
            SET ended_at = ?, total_items = ?, correct_items = ?, incorrect_items = ?
            WHERE id = ?
            """,
            (now, total_items, correct_items, incorrect_items, session_id),
        )
    streak_service.record_session_result(correct_items, incorrect_items)
    return {"message": "Đã hoàn tất phiên Flashcard.", "session_id": session_id}

