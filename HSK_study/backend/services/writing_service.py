"""Character writing practice: stroke-order tracing sessions and per-character mastery."""

from __future__ import annotations

from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError, ResourceNotFoundError


def get_random_characters(hsk_level: str | None, count: int) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if hsk_level:
        conditions.append("v.hsk_level = ?")
        parameters.append(hsk_level)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT v.hanzi, v.pinyin, v.meaning
            FROM vocabulary v
            {where_clause}
            ORDER BY RANDOM()
            LIMIT ?
            """,
            [*parameters, count * 6],
        ).fetchall()
        seen: dict[str, dict[str, Any]] = {}
        for row in rows:
            for character in row["hanzi"]:
                if character in seen or not ("一" <= character <= "鿿"):
                    continue
                seen[character] = {
                    "character": character,
                    "word": row["hanzi"],
                    "pinyin": row["pinyin"],
                    "meaning": row["meaning"],
                }
            if len(seen) >= count:
                break
        characters = list(seen.values())[:count]
        if not characters:
            return []
        placeholders = ",".join("?" * len(characters))
        progress_rows = connection.execute(
            f"""
            SELECT character, status, practice_count, success_count, last_practiced_at
            FROM writing_progress
            WHERE character IN ({placeholders})
            """,
            [item["character"] for item in characters],
        ).fetchall()
    progress_by_char = {row["character"]: dict(row) for row in progress_rows}
    for item in characters:
        progress = progress_by_char.get(item["character"])
        item["status"] = progress["status"] if progress else "new"
        item["practice_count"] = progress["practice_count"] if progress else 0
        item["success_count"] = progress["success_count"] if progress else 0
    return characters


def create_session(hsk_level: str | None, count: int) -> dict[str, Any]:
    characters = get_random_characters(hsk_level, count)
    if not characters:
        raise InvalidOperationError("Không có chữ Hán phù hợp để luyện viết.")
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO writing_sessions (hsk_level, started_at, total_items) VALUES (?, ?, ?)",
            (hsk_level or "all", now, len(characters)),
        )
        session_id = cursor.lastrowid
    return {"session_id": session_id, "hsk_level": hsk_level or "all", "characters": characters}


def _get_open_session(connection: Any, session_id: int) -> Any:
    session = connection.execute(
        "SELECT * FROM writing_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        raise ResourceNotFoundError("Không tìm thấy phiên luyện viết.")
    if session["ended_at"]:
        raise InvalidOperationError("Phiên luyện viết này đã kết thúc.")
    return session


def record_attempt(
    session_id: int, character: str, mistakes: int, is_correct: bool
) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        _get_open_session(connection, session_id)
        current = connection.execute(
            "SELECT * FROM writing_progress WHERE character = ?", (character,)
        ).fetchone()
        success_count = (current["success_count"] if current else 0) + (1 if is_correct else 0)
        status = "mastered" if success_count >= 3 else "learning"
        connection.execute(
            """
            INSERT INTO writing_progress (
                character, status, practice_count, success_count,
                last_practiced_at, created_at, updated_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(character) DO UPDATE SET
                status = excluded.status,
                practice_count = writing_progress.practice_count + 1,
                success_count = writing_progress.success_count + excluded.success_count,
                last_practiced_at = excluded.last_practiced_at,
                updated_at = excluded.updated_at
            """,
            (character, status, 1 if is_correct else 0, now, now, now),
        )
        connection.execute(
            """
            INSERT INTO writing_attempts (session_id, character, mistakes, is_correct, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, character, mistakes, int(is_correct), now),
        )
    return {
        "message": "Đã lưu kết quả luyện viết.",
        "session_id": session_id,
        "character": character,
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
            UPDATE writing_sessions
            SET ended_at = ?, total_items = ?, correct_items = ?, incorrect_items = ?
            WHERE id = ?
            """,
            (now, total_items, correct_items, incorrect_items, session_id),
        )
    return {"message": "Đã hoàn tất phiên luyện viết.", "session_id": session_id}


def get_progress_summary() -> dict[str, Any]:
    with get_connection() as connection:
        counts = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status = 'learning' THEN 1 ELSE 0 END) AS learning_count,
                   SUM(CASE WHEN status = 'mastered' THEN 1 ELSE 0 END) AS mastered_count
            FROM writing_progress
            """
        ).fetchone()
        recent = connection.execute(
            """
            SELECT character, status, practice_count, success_count, last_practiced_at
            FROM writing_progress
            ORDER BY last_practiced_at DESC
            LIMIT 12
            """
        ).fetchall()
    return {
        "practiced_count": counts["total"] or 0,
        "learning_count": counts["learning_count"] or 0,
        "mastered_count": counts["mastered_count"] or 0,
        "recent_characters": [dict(row) for row in recent],
    }
