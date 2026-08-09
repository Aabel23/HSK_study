"""Learning progress updates and summaries."""

from __future__ import annotations

from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import ResourceNotFoundError


def _vocabulary_exists(connection: Any, vocabulary_id: int) -> bool:
    return connection.execute(
        "SELECT 1 FROM vocabulary WHERE id = ?", (vocabulary_id,)
    ).fetchone() is not None


def get_item_progress(vocabulary_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT v.id AS vocabulary_id, v.hanzi, v.pinyin, v.meaning,
                   COALESCE(p.status, 'new') AS status,
                   COALESCE(p.review_count, 0) AS review_count,
                   COALESCE(p.correct_count, 0) AS correct_count,
                   COALESCE(p.incorrect_count, 0) AS incorrect_count,
                   p.last_reviewed_at, p.created_at, p.updated_at
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            WHERE v.id = ?
            """,
            (vocabulary_id,),
        ).fetchone()
    if not row:
        raise ResourceNotFoundError("Không tìm thấy từ vựng.")
    return dict(row)


def update_status(vocabulary_id: int, status: str) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        if not _vocabulary_exists(connection, vocabulary_id):
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")
        connection.execute(
            """
            INSERT INTO learning_progress (
                vocabulary_id, status, review_count, correct_count,
                incorrect_count, last_reviewed_at, created_at, updated_at
            ) VALUES (?, ?, 0, 0, 0, ?, ?, ?)
            ON CONFLICT(vocabulary_id) DO UPDATE SET
                status = excluded.status,
                last_reviewed_at = excluded.last_reviewed_at,
                updated_at = excluded.updated_at
            """,
            (vocabulary_id, status, now, now, now),
        )
    return get_item_progress(vocabulary_id)


def get_progress_summary() -> dict[str, Any]:
    with get_connection() as connection:
        counts = connection.execute(
            """
            SELECT COUNT(v.id) AS total_vocabulary,
                   SUM(CASE WHEN COALESCE(p.status, 'new') = 'new' THEN 1 ELSE 0 END) AS new_count,
                   SUM(CASE WHEN p.status = 'learning' THEN 1 ELSE 0 END) AS learning_count,
                   SUM(CASE WHEN p.status = 'review' THEN 1 ELSE 0 END) AS review_count,
                   SUM(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered_count
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            """
        ).fetchone()
        review_items = connection.execute(
            """
            SELECT v.id, v.hanzi, v.pinyin, v.meaning, p.status,
                   p.review_count, p.correct_count, p.incorrect_count, p.last_reviewed_at
            FROM learning_progress p
            JOIN vocabulary v ON v.id = p.vocabulary_id
            WHERE p.status = 'review'
            ORDER BY p.last_reviewed_at DESC, v.id
            LIMIT 12
            """
        ).fetchall()
        mastered_items = connection.execute(
            """
            SELECT v.id, v.hanzi, v.pinyin, v.meaning, p.status,
                   p.review_count, p.correct_count, p.last_reviewed_at
            FROM learning_progress p
            JOIN vocabulary v ON v.id = p.vocabulary_id
            WHERE p.status = 'mastered'
            ORDER BY p.last_reviewed_at DESC, v.id
            LIMIT 12
            """
        ).fetchall()
        recent_sessions = connection.execute(
            """
            SELECT * FROM (
                SELECT id, session_type, started_at, ended_at, total_items,
                       correct_items, incorrect_items
                FROM study_sessions
                UNION ALL
                SELECT id, 'sentence' AS session_type, started_at, ended_at,
                       total_items, correct_items, incorrect_items
                FROM sentence_sessions
            )
            ORDER BY started_at DESC
            LIMIT 10
            """
        ).fetchall()

    total = counts["total_vocabulary"] or 0
    mastered = counts["mastered_count"] or 0
    return {
        "total_vocabulary": total,
        "new_count": counts["new_count"] or 0,
        "learning_count": counts["learning_count"] or 0,
        "review_count": counts["review_count"] or 0,
        "mastered_count": mastered,
        "completion_percentage": round(mastered / total * 100, 1) if total else 0,
        "review_items": [dict(row) for row in review_items],
        "mastered_items": [dict(row) for row in mastered_items],
        "recent_sessions": [dict(row) for row in recent_sessions],
    }
