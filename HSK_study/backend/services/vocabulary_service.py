"""Vocabulary queries and filtering."""

from __future__ import annotations

from typing import Any

from backend.database import get_connection
from backend.services.errors import ResourceNotFoundError


SELECT_FIELDS = """
    v.id, v.hanzi, v.pinyin, v.meaning, v.example, v.example_pinyin,
    v.example_meaning, v.topic, v.created_at, v.updated_at,
    v.hsk_level, v.meaning_en, v.traditional, v.pos, v.pos_vi,
    v.classifiers, v.frequency,
    COALESCE(p.status, 'new') AS status,
    COALESCE(p.review_count, 0) AS review_count,
    COALESCE(p.correct_count, 0) AS correct_count,
    COALESCE(p.incorrect_count, 0) AS incorrect_count,
    p.last_reviewed_at
"""


def list_vocabulary(
    search: str | None = None,
    topic: str | None = None,
    status: str | None = None,
    hsk_level: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    conditions: list[str] = []
    parameters: list[Any] = []

    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            "(v.hanzi LIKE ? OR v.pinyin LIKE ? OR v.meaning LIKE ? OR v.meaning_en LIKE ?)"
        )
        parameters.extend([term, term, term, term])
    if topic:
        conditions.append("v.topic = ?")
        parameters.append(topic)
    if status:
        conditions.append("COALESCE(p.status, 'new') = ?")
        parameters.append(status)
    if hsk_level:
        conditions.append("v.hsk_level = ?")
        parameters.append(hsk_level)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_connection() as connection:
        total = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            {where_clause}
            """,
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT {SELECT_FIELDS}
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            {where_clause}
            ORDER BY v.id
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_vocabulary(vocabulary_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT {SELECT_FIELDS}
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            WHERE v.id = ?
            """,
            (vocabulary_id,),
        ).fetchone()
    if not row:
        raise ResourceNotFoundError("Không tìm thấy từ vựng.")
    return dict(row)


def get_random_vocabulary(
    count: int,
    status: str | None = None,
    include_mastered: bool = True,
    hsk_level: str | None = None,
    exclude_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if status:
        conditions.append("COALESCE(p.status, 'new') = ?")
        parameters.append(status)
    if not include_mastered:
        conditions.append("COALESCE(p.status, 'new') != 'mastered'")
    if hsk_level:
        conditions.append("v.hsk_level = ?")
        parameters.append(hsk_level)
    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        conditions.append(f"v.id NOT IN ({placeholders})")
        parameters.extend(exclude_ids)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT {SELECT_FIELDS}
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            {where_clause}
            ORDER BY RANDOM()
            LIMIT ?
            """,
            [*parameters, count],
        ).fetchall()
    return [dict(row) for row in rows]


def list_topics() -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT topic FROM vocabulary WHERE topic IS NOT NULL ORDER BY topic"
        ).fetchall()
    return [row[0] for row in rows]


HSK_LEVEL_ORDER = ["1", "2", "3", "4", "5", "6", "7-9"]


def list_hsk_levels() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT v.hsk_level AS level,
                   COUNT(v.id) AS total,
                   SUM(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            GROUP BY v.hsk_level
            """
        ).fetchall()
    by_level = {row["level"]: dict(row) for row in rows}
    return [
        {
            "level": level,
            "total": by_level.get(level, {}).get("total", 0) or 0,
            "mastered": by_level.get(level, {}).get("mastered", 0) or 0,
        }
        for level in HSK_LEVEL_ORDER
    ]

