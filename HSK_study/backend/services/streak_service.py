"""Daily study activity, streaks and experience points.

Activity is bucketed by *local* calendar date rather than UTC: a streak is a
human habit, so it should break at the learner's midnight, not London's.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import settings_service

XP_BY_RATING = {"again": 2, "hard": 5, "good": 8, "easy": 10}
XP_PER_CORRECT_ANSWER = 6
XP_PER_LEVEL = 500


def xp_for_rating(rating: str) -> int:
    return XP_BY_RATING.get(rating, XP_PER_CORRECT_ANSWER)


def _today() -> str:
    return date.today().isoformat()


def record_activity(
    *,
    correct: bool = True,
    new_learned: int = 0,
    xp: int = 0,
    seconds: int = 0,
    reviews: int = 1,
    connection: Any = None,
) -> None:
    """Fold one study action into today's activity row.

    ``connection`` is accepted so a caller already inside a transaction can pass
    its own handle; when ``None`` a short-lived connection is opened.
    """
    now = utc_now()
    today = _today()
    params = (
        today, reviews, 1 if correct else 0, 0 if correct else 1,
        new_learned, seconds, xp, now, now,
    )
    statement = """
        INSERT INTO daily_activity (
            activity_date, reviews_done, correct_count, incorrect_count,
            new_learned, study_seconds, xp, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(activity_date) DO UPDATE SET
            reviews_done = daily_activity.reviews_done + excluded.reviews_done,
            correct_count = daily_activity.correct_count + excluded.correct_count,
            incorrect_count = daily_activity.incorrect_count + excluded.incorrect_count,
            new_learned = daily_activity.new_learned + excluded.new_learned,
            study_seconds = daily_activity.study_seconds + excluded.study_seconds,
            xp = daily_activity.xp + excluded.xp,
            updated_at = excluded.updated_at
    """
    if connection is not None:
        connection.execute(statement, params)
        return
    with get_connection() as owned_connection:
        owned_connection.execute(statement, params)


def record_session_result(correct_items: int, incorrect_items: int, seconds: int = 0) -> None:
    """Record a finished practice session (quiz, matching, listening, ...)."""
    total = max(0, correct_items) + max(0, incorrect_items)
    if total == 0:
        return
    now = utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO daily_activity (
                activity_date, reviews_done, correct_count, incorrect_count,
                new_learned, study_seconds, xp, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
            ON CONFLICT(activity_date) DO UPDATE SET
                reviews_done = daily_activity.reviews_done + excluded.reviews_done,
                correct_count = daily_activity.correct_count + excluded.correct_count,
                incorrect_count = daily_activity.incorrect_count + excluded.incorrect_count,
                study_seconds = daily_activity.study_seconds + excluded.study_seconds,
                xp = daily_activity.xp + excluded.xp,
                updated_at = excluded.updated_at
            """,
            (
                _today(), total, max(0, correct_items), max(0, incorrect_items),
                max(0, seconds), max(0, correct_items) * XP_PER_CORRECT_ANSWER, now, now,
            ),
        )


def _streaks(active_days: list[str]) -> tuple[int, int]:
    """Return (current, longest) streak lengths from sorted ISO date strings."""
    if not active_days:
        return 0, 0
    days = sorted({datetime.fromisoformat(day).date() for day in active_days})
    longest = 1
    run = 1
    for previous, current in zip(days, days[1:]):
        if (current - previous).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    today = date.today()
    last = days[-1]
    # Yesterday still counts as "alive" so the streak survives until midnight.
    if (today - last).days > 1:
        return 0, longest
    current_streak = 1
    for previous, following in zip(reversed(days[:-1]), reversed(days[1:])):
        if (following - previous).days == 1:
            current_streak += 1
        else:
            break
    return current_streak, longest


def get_summary(heatmap_days: int = 182) -> dict[str, Any]:
    """Streak, XP level, today's goal progress and a contribution heatmap."""
    today = _today()
    since = (date.today() - timedelta(days=heatmap_days - 1)).isoformat()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT activity_date, reviews_done, correct_count, incorrect_count,
                   new_learned, study_seconds, xp
            FROM daily_activity
            ORDER BY activity_date ASC
            """
        ).fetchall()

    by_date = {row["activity_date"]: dict(row) for row in rows}
    active_days = [row["activity_date"] for row in rows if (row["reviews_done"] or 0) > 0]
    current_streak, longest_streak = _streaks(active_days)

    total_xp = sum(row["xp"] or 0 for row in rows)
    today_row = by_date.get(today, {})
    daily_goal = int(settings_service.get_setting("daily_goal") or 20)
    today_reviews = int(today_row.get("reviews_done") or 0)

    heatmap = []
    start = date.fromisoformat(since)
    for offset in range((date.today() - start).days + 1):
        day = (start + timedelta(days=offset)).isoformat()
        entry = by_date.get(day)
        heatmap.append({"date": day, "count": int(entry["reviews_done"]) if entry else 0})

    level = total_xp // XP_PER_LEVEL + 1
    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "active_days": len(active_days),
        "total_xp": total_xp,
        "level": level,
        "xp_into_level": total_xp % XP_PER_LEVEL,
        "xp_per_level": XP_PER_LEVEL,
        "daily_goal": daily_goal,
        "today_reviews": today_reviews,
        "today_correct": int(today_row.get("correct_count") or 0),
        "today_incorrect": int(today_row.get("incorrect_count") or 0),
        "today_new_learned": int(today_row.get("new_learned") or 0),
        "today_xp": int(today_row.get("xp") or 0),
        "goal_percentage": round(min(100.0, today_reviews / daily_goal * 100), 1) if daily_goal else 0.0,
        "goal_met": today_reviews >= daily_goal,
        "heatmap": heatmap,
        "history": [dict(row) for row in rows[-30:]],
    }
