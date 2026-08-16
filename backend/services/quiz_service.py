"""Multiple-choice quiz/test sessions built from the vocabulary bank."""

from __future__ import annotations

import json
import random
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import mcq, session_store, srs_service
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.session_store import SessionKind


DEFAULT_QUESTION_TYPES = ["mcq_meaning", "mcq_hanzi", "mcq_pinyin", "mcq_audio"]
OPTION_COUNT = mcq.OPTION_COUNT

#: Which field of the word each mode puts on the buttons.
LABEL_FIELD_BY_TYPE = {
    "mcq_meaning": "meaning",
    "mcq_hanzi": "hanzi",
    "mcq_pinyin": "pinyin",
    "mcq_audio": "meaning",
}

SESSION = SessionKind(
    table="quiz_sessions",
    not_found="Không tìm thấy phiên kiểm tra.",
    already_ended="Phiên kiểm tra này đã kết thúc.",
    completed="Đã hoàn tất bài kiểm tra.",
)


def _build_prompt(question_type: str, target: dict[str, Any]) -> dict[str, Any]:
    """What the learner is shown. Never includes the field they must choose."""
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
    if question_type not in LABEL_FIELD_BY_TYPE:
        raise InvalidOperationError("Loại câu hỏi không hợp lệ.")
    question = mcq.draw(
        hsk_level,
        LABEL_FIELD_BY_TYPE[question_type],
        empty_message="Không có từ phù hợp để tạo câu hỏi.",
    )
    return {
        "question_type": question_type,
        "target_vocabulary_id": question.target["id"],
        "prompt": _build_prompt(question_type, question.target),
        "options": question.options,
    }


def _batch(
    count: int, question_types: list[str], pick_level: Any
) -> list[dict[str, Any]]:
    active_types = question_types or list(DEFAULT_QUESTION_TYPES)
    return [
        {**_generate_one(pick_level(), random.choice(active_types)), "question_id": index}
        for index in range(count)
    ]


def generate_questions(
    hsk_levels: list[str] | None, question_types: list[str], count: int
) -> list[dict[str, Any]]:
    """Build a mixed batch of multiple-choice questions.

    Unlike :func:`create_session` this takes *several* HSK levels and picks one
    per question, which is what the HSK mock exam needs — a paper covers a band
    (HSK 1-2, HSK 3-4) rather than a single level. No session row is written, so
    the caller owns the bookkeeping.
    """
    return _batch(
        count,
        question_types,
        lambda: random.choice(hsk_levels) if hsk_levels else None,
    )


def create_session(
    hsk_level: str | None, question_types: list[str], count: int
) -> dict[str, Any]:
    active_types = question_types or list(DEFAULT_QUESTION_TYPES)
    session_id = session_store.start(
        SESSION,
        hsk_level=hsk_level or "all",
        question_types_json=json.dumps(active_types),
        total_items=count,
    )
    return {
        "session_id": session_id,
        "hsk_level": hsk_level or "all",
        "questions": _batch(count, active_types, lambda: hsk_level),
    }


def record_attempt(
    session_id: int, vocabulary_id: int, question_type: str, is_correct: bool
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
            INSERT INTO quiz_attempts (
                session_id, vocabulary_id, question_type, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, vocabulary_id, question_type, int(is_correct), utc_now()),
        )
    # A wrong answer here is evidence for the review queue; see
    # `srs_service.record_lapse` for why a right answer is not.
    if not is_correct:
        srs_service.record_lapse(vocabulary_id, source="quiz")

    return {
        "message": "Đã ghi nhận câu trả lời.",
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
    """Totals across every finished quiz, however the questions were asked.

    Counted from the session rows rather than from `quiz_attempts`: the reading
    half of the mock exam also runs through here, and its questions are passages
    and clause-ordering tasks that have no single `vocabulary_id` to attach an
    attempt row to. Both paths write the session totals, so this stays correct
    for the older per-word quizzes too.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS sessions,
                   COALESCE(SUM(correct_items), 0) AS correct,
                   COALESCE(SUM(incorrect_items), 0) AS incorrect
            FROM quiz_sessions
            WHERE ended_at IS NOT NULL
            """
        ).fetchone()
    correct = row["correct"] or 0
    incorrect = row["incorrect"] or 0
    return {
        "sessions": row["sessions"] or 0,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": session_store.accuracy(correct, incorrect),
    }
