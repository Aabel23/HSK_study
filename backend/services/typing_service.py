"""Typing practice: recall a word by typing it rather than recognising it.

Multiple choice lets a learner pick the right answer without being able to
produce it. Typing forces active recall, which is why this drill exists
alongside the quiz. Answers are graded by :mod:`backend.services.pinyin_utils`,
which accepts tone marks, tone numbers or no tones and reports tone accuracy
separately so the UI can coach instead of just failing the attempt.
"""

from __future__ import annotations

from typing import Any

from backend.database import get_connection, utc_now
from backend.services import pinyin_utils, streak_service
from backend.services.errors import InvalidOperationError, ResourceNotFoundError

MODES = {
    "hanzi_to_pinyin": "Nhìn chữ Hán, gõ pinyin",
    "audio_to_pinyin": "Nghe phát âm, gõ pinyin",
    "meaning_to_pinyin": "Nhìn nghĩa, gõ pinyin",
    "audio_to_hanzi": "Nghe phát âm, gõ chữ Hán",
    "meaning_to_hanzi": "Nhìn nghĩa, gõ chữ Hán",
}

# Modes whose expected answer is Chinese characters rather than pinyin.
HANZI_MODES = {"audio_to_hanzi", "meaning_to_hanzi"}

XP_CORRECT = 8
XP_CORRECT_WITH_TONES = 10


def _prompt_for(mode: str, row: Any) -> dict[str, Any]:
    """Only expose the fields the mode is allowed to reveal."""
    prompt: dict[str, Any] = {}
    if mode == "hanzi_to_pinyin":
        prompt["hanzi"] = row["hanzi"]
        prompt["meaning"] = row["meaning"]
    elif mode == "meaning_to_pinyin":
        prompt["meaning"] = row["meaning"]
    elif mode == "meaning_to_hanzi":
        prompt["meaning"] = row["meaning"]
        prompt["pinyin"] = row["pinyin"]
    elif mode in {"audio_to_pinyin", "audio_to_hanzi"}:
        # The audio endpoint needs the text, but the answer must stay hidden;
        # the client plays /api/audio?text=... without ever displaying it.
        prompt["audio_text"] = row["hanzi"]
    return prompt


def create_session(
    hsk_level: str | None, mode: str, count: int, only_due: bool = False
) -> dict[str, Any]:
    if mode not in MODES:
        raise InvalidOperationError("Chế độ luyện gõ không hợp lệ.")

    conditions = ["v.pinyin IS NOT NULL", "v.pinyin != ''"]
    parameters: list[Any] = []
    if hsk_level:
        conditions.append("v.hsk_level = ?")
        parameters.append(hsk_level)
    if only_due:
        conditions.append("p.due_at IS NOT NULL AND p.due_at <= ?")
        parameters.append(utc_now())

    where_clause = f"WHERE {' AND '.join(conditions)}"
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT v.id, v.hanzi, v.pinyin, v.meaning, v.hsk_level
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            {where_clause}
            ORDER BY RANDOM()
            LIMIT ?
            """,
            [*parameters, count],
        ).fetchall()
        if not rows:
            raise InvalidOperationError("Không có từ phù hợp để luyện gõ.")
        cursor = connection.execute(
            """
            INSERT INTO typing_sessions (hsk_level, mode, started_at, total_items)
            VALUES (?, ?, ?, ?)
            """,
            (hsk_level or "all", mode, utc_now(), len(rows)),
        )
        session_id = cursor.lastrowid

    items = [
        {
            "item_id": index,
            "vocabulary_id": row["id"],
            "mode": mode,
            "hsk_level": row["hsk_level"],
            "prompt": _prompt_for(mode, row),
        }
        for index, row in enumerate(rows)
    ]
    return {"session_id": session_id, "mode": mode, "hsk_level": hsk_level or "all", "items": items}


def check_answer(
    session_id: int | None, vocabulary_id: int, mode: str, answer: str
) -> dict[str, Any]:
    """Grade one typed answer, persist it, and reveal the full word."""
    if mode not in MODES:
        raise InvalidOperationError("Chế độ luyện gõ không hợp lệ.")

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, hanzi, pinyin, meaning FROM vocabulary WHERE id = ?",
            (vocabulary_id,),
        ).fetchone()
        if not row:
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")

        if mode in HANZI_MODES:
            expected = row["hanzi"]
            is_correct = pinyin_utils.compare_hanzi(expected, answer)
            tones_correct = is_correct
            tones_provided = True
            diff = pinyin_utils.character_diff(expected, answer)
        else:
            expected = row["pinyin"]
            comparison = pinyin_utils.compare_pinyin(expected, answer)
            is_correct = comparison.is_correct
            tones_correct = comparison.tones_correct
            tones_provided = comparison.tones_provided
            diff = []

        connection.execute(
            """
            INSERT INTO typing_attempts (
                session_id, vocabulary_id, mode, answer, expected, is_correct, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, vocabulary_id, mode, answer[:200], expected, 1 if is_correct else 0, utc_now()),
        )

    streak_service.record_activity(
        correct=is_correct,
        xp=(XP_CORRECT_WITH_TONES if tones_correct else XP_CORRECT) if is_correct else 0,
    )

    return {
        "vocabulary_id": vocabulary_id,
        "is_correct": is_correct,
        "tones_correct": tones_correct,
        "tones_provided": tones_provided,
        "expected": expected,
        "answer": answer,
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
    now = utc_now()
    with get_connection() as connection:
        session = connection.execute(
            "SELECT id, ended_at FROM typing_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise ResourceNotFoundError("Không tìm thấy phiên luyện gõ.")
        if session["ended_at"]:
            raise InvalidOperationError("Phiên luyện gõ đã kết thúc.")
        connection.execute(
            """
            UPDATE typing_sessions
            SET ended_at = ?, total_items = ?, correct_items = ?, incorrect_items = ?
            WHERE id = ?
            """,
            (now, total_items, correct_items, incorrect_items, session_id),
        )
    return {"message": "Đã hoàn tất phiên luyện gõ.", "session_id": session_id}


def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM typing_sessions WHERE ended_at IS NOT NULL) AS sessions,
                (SELECT COUNT(*) FROM typing_attempts) AS attempts,
                (SELECT COUNT(*) FROM typing_attempts WHERE is_correct = 1) AS correct
            """
        ).fetchone()
        by_mode = connection.execute(
            """
            SELECT mode,
                   COUNT(*) AS attempts,
                   SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM typing_attempts
            GROUP BY mode
            """
        ).fetchall()

    attempts = row["attempts"] or 0
    correct = row["correct"] or 0
    return {
        "sessions": row["sessions"] or 0,
        "attempts": attempts,
        "correct": correct,
        "incorrect": attempts - correct,
        "accuracy": round(correct / attempts * 100, 1) if attempts else 0.0,
        "modes": [
            {
                "mode": entry["mode"],
                "label": MODES.get(entry["mode"], entry["mode"]),
                "attempts": entry["attempts"],
                "correct": entry["correct"] or 0,
                "accuracy": round((entry["correct"] or 0) / entry["attempts"] * 100, 1)
                if entry["attempts"]
                else 0.0,
            }
            for entry in by_mode
        ],
    }
