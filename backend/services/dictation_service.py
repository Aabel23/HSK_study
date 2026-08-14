"""Dictation: listen and write down what you heard.

This is the hardest and most valuable listening drill, because nothing on
screen gives the answer away -- the learner has to segment the audio and
reproduce it. Word dictation builds vocabulary recall; sentence dictation
additionally trains parsing connected speech.

Replay counts are stored so the stats can distinguish "heard it once" from
"needed six replays", which is the real measure of listening progress.
"""

from __future__ import annotations

from typing import Any

from backend.database import get_connection, utc_now
from backend.services import pinyin_utils, session_store, streak_service
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.session_store import SessionKind

SESSION = SessionKind(
    table="dictation_sessions",
    not_found="Không tìm thấy phiên nghe chép.",
    already_ended="Phiên nghe chép đã kết thúc.",
    completed="Đã hoàn tất phiên nghe chép.",
)

MODES = {
    "word_pinyin": "Nghe từ, gõ pinyin",
    "word_hanzi": "Nghe từ, gõ chữ Hán",
    "sentence_hanzi": "Nghe câu, gõ lại câu",
}
SENTENCE_MODES = {"sentence_hanzi"}

XP_CORRECT = 10
# Replaying is part of learning, but a first-listen success deserves more.
XP_FIRST_LISTEN_BONUS = 4


def create_session(hsk_level: str | None, mode: str, count: int) -> dict[str, Any]:
    if mode not in MODES:
        raise InvalidOperationError("Chế độ nghe chép không hợp lệ.")

    parameters: list[Any] = []
    if mode in SENTENCE_MODES:
        conditions = []
        if hsk_level:
            conditions.append("hsk_level = ?")
            parameters.append(hsk_level)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, hanzi, pinyin, meaning, hsk_level, difficulty
            FROM sentences
            {where_clause}
            ORDER BY RANDOM()
            LIMIT ?
        """
    else:
        conditions = ["v.pinyin IS NOT NULL", "v.pinyin != ''"]
        if hsk_level:
            conditions.append("v.hsk_level = ?")
            parameters.append(hsk_level)
        query = f"""
            SELECT v.id, v.hanzi, v.pinyin, v.meaning, v.hsk_level
            FROM vocabulary v
            WHERE {' AND '.join(conditions)}
            ORDER BY RANDOM()
            LIMIT ?
        """

    with get_connection() as connection:
        rows = connection.execute(query, [*parameters, count]).fetchall()
        if not rows:
            raise InvalidOperationError("Không có nội dung phù hợp để nghe chép.")

    session_id = session_store.start(
        SESSION, hsk_level=hsk_level or "all", mode=mode, total_items=len(rows)
    )
    is_sentence = mode in SENTENCE_MODES
    items = [
        {
            "item_id": index,
            "mode": mode,
            "target_id": row["id"],
            "is_sentence": is_sentence,
            # The client passes this to /api/audio to synthesise speech. It is
            # deliberately the only text sent, and the UI must not render it.
            "audio_text": row["hanzi"],
            "hsk_level": row["hsk_level"],
            "hint": {
                "length": len(row["hanzi"]),
                "meaning": row["meaning"] if is_sentence else None,
            },
        }
        for index, row in enumerate(rows)
    ]
    return {
        "session_id": session_id,
        "mode": mode,
        "hsk_level": hsk_level or "all",
        "items": items,
    }


def check_answer(
    session_id: int | None,
    target_id: int,
    mode: str,
    answer: str,
    replays: int = 0,
) -> dict[str, Any]:
    """Grade one dictation answer and reveal the full text."""
    if mode not in MODES:
        raise InvalidOperationError("Chế độ nghe chép không hợp lệ.")
    is_sentence = mode in SENTENCE_MODES

    with get_connection() as connection:
        table = "sentences" if is_sentence else "vocabulary"
        row = connection.execute(
            f"SELECT id, hanzi, pinyin, meaning FROM {table} WHERE id = ?", (target_id,)
        ).fetchone()
        if not row:
            raise ResourceNotFoundError(
                "Không tìm thấy câu." if is_sentence else "Không tìm thấy từ vựng."
            )

        if mode == "word_pinyin":
            expected = row["pinyin"]
            comparison = pinyin_utils.compare_pinyin(expected, answer)
            is_correct = comparison.is_correct
            tones_correct = comparison.tones_correct
            tones_provided = comparison.tones_provided
            diff: list[dict[str, object]] = []
        else:
            expected = row["hanzi"]
            is_correct = pinyin_utils.compare_hanzi(expected, answer)
            tones_correct = is_correct
            tones_provided = True
            diff = pinyin_utils.character_diff(expected, answer)

        connection.execute(
            """
            INSERT INTO dictation_attempts (
                session_id, vocabulary_id, sentence_id, mode, answer, expected,
                replays, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                None if is_sentence else target_id,
                target_id if is_sentence else None,
                mode,
                answer[:500],
                expected,
                max(0, replays),
                1 if is_correct else 0,
                utc_now(),
            ),
        )

    xp = 0
    if is_correct:
        xp = XP_CORRECT + (XP_FIRST_LISTEN_BONUS if replays <= 1 else 0)
    streak_service.record_activity(correct=is_correct, xp=xp)

    return {
        "target_id": target_id,
        "is_correct": is_correct,
        "tones_correct": tones_correct,
        "tones_provided": tones_provided,
        "expected": expected,
        "answer": answer,
        "replays": replays,
        "character_diff": diff,
        "reveal": {
            "hanzi": row["hanzi"],
            "pinyin": row["pinyin"],
            "meaning": row["meaning"],
        },
    }


def complete_session(
    session_id: int, total_items: int, correct_items: int, incorrect_items: int
) -> dict[str, Any]:
    # `check_answer` already credited the streak for each item heard.
    return session_store.complete(
        SESSION, session_id, total_items, correct_items, incorrect_items,
        record_streak=False,
    )


def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM dictation_sessions WHERE ended_at IS NOT NULL) AS sessions,
                (SELECT COUNT(*) FROM dictation_attempts) AS attempts,
                (SELECT COUNT(*) FROM dictation_attempts WHERE is_correct = 1) AS correct,
                (SELECT AVG(replays) FROM dictation_attempts) AS average_replays,
                (SELECT COUNT(*) FROM dictation_attempts
                 WHERE is_correct = 1 AND replays <= 1) AS first_listen_correct
            """
        ).fetchone()

    attempts = row["attempts"] or 0
    correct = row["correct"] or 0
    return {
        "sessions": row["sessions"] or 0,
        "attempts": attempts,
        "correct": correct,
        "incorrect": attempts - correct,
        "accuracy": round(correct / attempts * 100, 1) if attempts else 0.0,
        "average_replays": round(row["average_replays"] or 0, 2),
        "first_listen_correct": row["first_listen_correct"] or 0,
        "first_listen_rate": round((row["first_listen_correct"] or 0) / attempts * 100, 1)
        if attempts
        else 0.0,
    }
