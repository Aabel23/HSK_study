"""Listening practice: hear a word spoken, pick the correct meaning or hanzi."""

from __future__ import annotations

from typing import Any

from backend.database import get_connection, utc_now
from backend.services import mcq, session_store, srs_service
from backend.services.errors import ResourceNotFoundError
from backend.services.session_store import SessionKind


OPTION_COUNT = mcq.OPTION_COUNT
LABEL_FIELD_BY_MODE = {
    "audio_to_meaning": "meaning",
    "audio_to_hanzi": "hanzi",
}

SESSION = SessionKind(
    table="listening_sessions",
    not_found="Không tìm thấy phiên luyện nghe.",
    already_ended="Phiên luyện nghe này đã kết thúc.",
    completed="Đã hoàn tất bài luyện nghe.",
)


def _generate_one(hsk_level: str | None, mode: str) -> dict[str, Any]:
    question = mcq.draw(
        hsk_level,
        LABEL_FIELD_BY_MODE[mode],
        empty_message="Không có từ phù hợp để tạo bài nghe.",
    )
    return {
        "mode": mode,
        "target_vocabulary_id": question.target["id"],
        # The client passes this to /api/audio; the answer itself is never shown.
        "audio_text": question.target["hanzi"],
        "options": question.options,
    }


def create_session(hsk_level: str | None, mode: str, count: int) -> dict[str, Any]:
    session_id = session_store.start(
        SESSION, hsk_level=hsk_level or "all", mode=mode, total_items=count
    )
    items = [
        {**_generate_one(hsk_level, mode), "item_id": index} for index in range(count)
    ]
    return {
        "session_id": session_id,
        "hsk_level": hsk_level or "all",
        "mode": mode,
        "items": items,
    }


def record_attempt(
    session_id: int, vocabulary_id: int, mode: str, is_correct: bool
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
            INSERT INTO listening_attempts (
                session_id, vocabulary_id, mode, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, vocabulary_id, mode, int(is_correct), utc_now()),
        )
    # A wrong answer here is evidence for the review queue; see
    # `srs_service.record_lapse` for why a right answer is not.
    if not is_correct:
        srs_service.record_lapse(vocabulary_id, source="listening")

    return {
        "message": "Đã ghi nhận lần nghe.",
        "session_id": session_id,
        "vocabulary_id": vocabulary_id,
        "is_correct": is_correct,
    }


def complete_session(
    session_id: int, total_items: int, correct_items: int, incorrect_items: int
) -> dict[str, Any]:
    return session_store.complete(
        SESSION, session_id, total_items, correct_items, incorrect_items
    )


def get_stats() -> dict[str, Any]:
    return session_store.attempt_stats(SESSION, "listening_attempts")
