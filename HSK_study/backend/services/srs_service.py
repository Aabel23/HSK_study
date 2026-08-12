"""Spaced repetition scheduling (SM-2) on top of the existing progress table.

The classic SuperMemo-2 algorithm is used because it needs only the four values
already stored per word (ease factor, interval, repetition count, due date) and
behaves predictably offline, which matters for a desktop app with no server.
Ratings map to SM-2 quality scores: again=0, hard=3, good=4, easy=5.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import streak_service
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.services.vocabulary_service import SELECT_FIELDS

RATING_QUALITY = {"again": 0, "hard": 3, "good": 4, "easy": 5}
MINIMUM_EASE = 1.3
DEFAULT_EASE = 2.5
# A lapsed card comes back in ten minutes rather than a full day so the user can
# actually fix it inside the same session.
RELEARN_INTERVAL_DAYS = 10 / (24 * 60)
MASTERED_INTERVAL_DAYS = 21.0

# SELECT_FIELDS already exposes the scheduling columns, so the queue reuses it
# verbatim and the API returns the same vocabulary shape everywhere.
REVIEW_SELECT = f"""
    SELECT {SELECT_FIELDS}
    FROM vocabulary v
    LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _next_ease(current: float, quality: int) -> float:
    """SM-2 ease update, clamped so a word never becomes impossible to schedule."""
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    return max(MINIMUM_EASE, round(current + delta, 4))


def _next_interval(interval: float, repetitions: int, ease: float, rating: str) -> float:
    if rating == "again":
        return RELEARN_INTERVAL_DAYS
    if repetitions <= 1:
        return 1.0 if rating != "easy" else 3.0
    if repetitions == 2:
        return 6.0 if rating != "easy" else 8.0
    grown = max(interval, 1.0) * ease
    if rating == "hard":
        grown = max(interval, 1.0) * 1.2
    elif rating == "easy":
        grown *= 1.3
    return round(min(grown, 365.0), 4)


def _status_for(interval: float, repetitions: int, rating: str) -> str:
    """Map the SM-2 state onto the four statuses the rest of the app already uses.

    A word stays "learning" until it has graduated past its introduction (two
    successful reviews), then cycles as "review", and is "mastered" once the
    interval reaches three weeks.
    """
    if rating == "again" or repetitions <= 1:
        return "learning"
    if interval >= MASTERED_INTERVAL_DAYS:
        return "mastered"
    return "review"


def _row_to_item(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["is_favorite"] = bool(item.get("is_favorite", 0))
    return item


def get_due_queue(
    limit: int = 20,
    hsk_level: str | None = None,
    include_new: bool = True,
    new_limit: int | None = None,
) -> dict[str, Any]:
    """Return words scheduled for today, topped up with new words if allowed.

    Seeding gives every word a ``learning_progress`` row up front, so a word is
    "new" when it has no schedule yet (``due_at IS NULL``) rather than when the
    join misses.
    """
    now_iso = utc_now()
    level_clause = "AND v.hsk_level = ?" if hsk_level else ""
    level_params: list[Any] = [hsk_level] if hsk_level else []

    with get_connection() as connection:
        due_rows = connection.execute(
            f"""
            {REVIEW_SELECT}
            WHERE p.id IS NOT NULL
              AND p.due_at IS NOT NULL
              AND p.due_at <= ?
              {level_clause}
            ORDER BY p.due_at ASC, v.frequency IS NULL, v.frequency ASC
            LIMIT ?
            """,
            [now_iso, *level_params, limit],
        ).fetchall()

        due_total = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM vocabulary v
            JOIN learning_progress p ON p.vocabulary_id = v.id
            WHERE p.due_at IS NOT NULL AND p.due_at <= ? {level_clause}
            """,
            [now_iso, *level_params],
        ).fetchone()[0]

        new_rows: list[Any] = []
        remaining = limit - len(due_rows)
        if include_new and remaining > 0:
            allowance = remaining if new_limit is None else min(remaining, max(new_limit, 0))
            if allowance > 0:
                new_rows = connection.execute(
                    f"""
                    {REVIEW_SELECT}
                    WHERE p.due_at IS NULL {level_clause}
                    ORDER BY v.hsk_level ASC, v.frequency IS NULL, v.frequency ASC, v.id ASC
                    LIMIT ?
                    """,
                    [*level_params, allowance],
                ).fetchall()

        new_total = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM vocabulary v
            LEFT JOIN learning_progress p ON p.vocabulary_id = v.id
            WHERE p.due_at IS NULL {level_clause}
            """,
            level_params,
        ).fetchone()[0]

    items = [_row_to_item(row) for row in due_rows] + [_row_to_item(row) for row in new_rows]
    return {
        "items": items,
        "due_count": due_total,
        "new_count": new_total,
        "returned": len(items),
    }


def submit_review(vocabulary_id: int, rating: str, source: str = "review") -> dict[str, Any]:
    """Apply an SM-2 update for one word and record it against today's activity."""
    if rating not in RATING_QUALITY:
        raise InvalidOperationError("Mức đánh giá không hợp lệ.")
    quality = RATING_QUALITY[rating]
    now = _now()
    now_iso = utc_now()

    with get_connection() as connection:
        exists = connection.execute(
            "SELECT 1 FROM vocabulary WHERE id = ?", (vocabulary_id,)
        ).fetchone()
        if not exists:
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")

        current = connection.execute(
            """
            SELECT COALESCE(ease_factor, ?) AS ease_factor,
                   COALESCE(interval_days, 0) AS interval_days,
                   COALESCE(repetitions, 0) AS repetitions,
                   COALESCE(lapses, 0) AS lapses,
                   COALESCE(review_count, 0) AS review_count,
                   COALESCE(correct_count, 0) AS correct_count,
                   COALESCE(incorrect_count, 0) AS incorrect_count
            FROM learning_progress WHERE vocabulary_id = ?
            """,
            (DEFAULT_EASE, vocabulary_id),
        ).fetchone()

        previous_interval = float(current["interval_days"]) if current else 0.0
        ease = float(current["ease_factor"]) if current else DEFAULT_EASE
        repetitions = int(current["repetitions"]) if current else 0
        lapses = int(current["lapses"]) if current else 0
        # Seeded rows exist with review_count 0, so "never reviewed" is the test
        # for a newly learned word rather than the absence of the row.
        is_first_review = current is None or int(current["review_count"]) == 0

        if rating == "again":
            repetitions = 0
            lapses += 1
        else:
            repetitions += 1
        ease = _next_ease(ease, quality)
        interval = _next_interval(previous_interval, repetitions, ease, rating)
        due_at = (now + timedelta(days=interval)).isoformat(timespec="seconds")
        status = _status_for(interval, repetitions, rating)
        correct = 0 if rating == "again" else 1

        connection.execute(
            """
            INSERT INTO learning_progress (
                vocabulary_id, status, review_count, correct_count, incorrect_count,
                last_reviewed_at, created_at, updated_at,
                ease_factor, interval_days, repetitions, lapses, due_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vocabulary_id) DO UPDATE SET
                status = excluded.status,
                review_count = learning_progress.review_count + 1,
                correct_count = learning_progress.correct_count + excluded.correct_count,
                incorrect_count = learning_progress.incorrect_count + excluded.incorrect_count,
                last_reviewed_at = excluded.last_reviewed_at,
                updated_at = excluded.updated_at,
                ease_factor = excluded.ease_factor,
                interval_days = excluded.interval_days,
                repetitions = excluded.repetitions,
                lapses = excluded.lapses,
                due_at = excluded.due_at
            """,
            (
                vocabulary_id, status, correct, 1 - correct, now_iso, now_iso, now_iso,
                ease, interval, repetitions, lapses, due_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO review_log (
                vocabulary_id, rating, previous_interval, next_interval,
                ease_factor, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (vocabulary_id, rating, previous_interval, interval, ease, source, now_iso),
        )

    streak_service.record_activity(
        connection=None,
        correct=correct == 1,
        new_learned=1 if is_first_review else 0,
        xp=streak_service.xp_for_rating(rating),
    )

    return {
        "vocabulary_id": vocabulary_id,
        "rating": rating,
        "status": status,
        "ease_factor": ease,
        "interval_days": interval,
        "repetitions": repetitions,
        "lapses": lapses,
        "due_at": due_at,
    }


def get_forecast(days: int = 14) -> list[dict[str, Any]]:
    """Number of cards falling due on each of the next ``days`` days."""
    now = _now()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT due_at FROM learning_progress WHERE due_at IS NOT NULL"
        ).fetchall()

    buckets = {index: 0 for index in range(days)}
    overdue = 0
    for row in rows:
        due = _parse_iso(row["due_at"])
        if due is None:
            continue
        offset = (due.date() - now.date()).days
        if offset < 0:
            overdue += 1
        elif offset < days:
            buckets[offset] += 1

    result = [
        {
            "date": (now + timedelta(days=index)).date().isoformat(),
            "offset": index,
            "count": buckets[index] + (overdue if index == 0 else 0),
        }
        for index in range(days)
    ]
    return result


def get_stats() -> dict[str, Any]:
    """Headline numbers for the review dashboard."""
    now_iso = utc_now()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM learning_progress
                 WHERE due_at IS NOT NULL AND due_at <= ?) AS due_now,
                (SELECT COUNT(*) FROM learning_progress WHERE due_at IS NOT NULL) AS in_rotation,
                (SELECT COUNT(*) FROM learning_progress WHERE status = 'mastered') AS mastered,
                (SELECT COUNT(*) FROM vocabulary) AS total_vocabulary,
                (SELECT COUNT(*) FROM review_log) AS total_reviews,
                (SELECT AVG(COALESCE(ease_factor, 2.5)) FROM learning_progress) AS average_ease,
                (SELECT COUNT(*) FROM learning_progress WHERE is_favorite = 1) AS favorites
            """,
            (now_iso,),
        ).fetchone()
        accuracy_row = connection.execute(
            """
            SELECT
                SUM(CASE WHEN rating != 'again' THEN 1 ELSE 0 END) AS good,
                COUNT(*) AS total
            FROM review_log
            """
        ).fetchone()

    total = accuracy_row["total"] or 0
    good = accuracy_row["good"] or 0
    return {
        "due_now": row["due_now"] or 0,
        "in_rotation": row["in_rotation"] or 0,
        "mastered": row["mastered"] or 0,
        "total_vocabulary": row["total_vocabulary"] or 0,
        "total_reviews": row["total_reviews"] or 0,
        "average_ease": round(row["average_ease"] or DEFAULT_EASE, 2),
        "favorites": row["favorites"] or 0,
        "retention_percentage": round(good / total * 100, 1) if total else 0.0,
        "forecast": get_forecast(),
    }


def set_favorite(vocabulary_id: int, is_favorite: bool) -> dict[str, Any]:
    """Bookmark a word so it can be filtered out of the full list later."""
    now_iso = utc_now()
    with get_connection() as connection:
        if not connection.execute(
            "SELECT 1 FROM vocabulary WHERE id = ?", (vocabulary_id,)
        ).fetchone():
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")
        connection.execute(
            """
            INSERT INTO learning_progress (
                vocabulary_id, status, created_at, updated_at, is_favorite
            ) VALUES (?, 'new', ?, ?, ?)
            ON CONFLICT(vocabulary_id) DO UPDATE SET
                is_favorite = excluded.is_favorite,
                updated_at = excluded.updated_at
            """,
            (vocabulary_id, now_iso, now_iso, 1 if is_favorite else 0),
        )
    return {"vocabulary_id": vocabulary_id, "is_favorite": is_favorite}


def set_note(vocabulary_id: int, note: str | None) -> dict[str, Any]:
    """Attach a personal memo to a word (``None`` or empty clears it)."""
    now_iso = utc_now()
    clean = (note or "").strip() or None
    with get_connection() as connection:
        if not connection.execute(
            "SELECT 1 FROM vocabulary WHERE id = ?", (vocabulary_id,)
        ).fetchone():
            raise ResourceNotFoundError("Không tìm thấy từ vựng.")
        connection.execute(
            """
            INSERT INTO learning_progress (
                vocabulary_id, status, created_at, updated_at, note
            ) VALUES (?, 'new', ?, ?, ?)
            ON CONFLICT(vocabulary_id) DO UPDATE SET
                note = excluded.note,
                updated_at = excluded.updated_at
            """,
            (vocabulary_id, now_iso, now_iso, clean),
        )
    return {"vocabulary_id": vocabulary_id, "note": clean}


def list_favorites(limit: int = 200) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            {REVIEW_SELECT}
            WHERE p.is_favorite = 1
            ORDER BY p.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_item(row) for row in rows]
