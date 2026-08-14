"""Shared lifecycle for every practice-session table.

Nine drills — flashcard, nối từ, luyện câu, luyện nghe, luyện gõ, nghe chép,
kiểm tra, thi thử — each keep their own session table, and each had grown its
own copy of the same four steps: insert a row when the session starts, look it
up and refuse it when it is missing or already submitted, stamp the totals on
it when it ends, and fold the result into the daily streak.

The copies differed only in the table name and the Vietnamese noun in the error
message, so the lifecycle lives here once and each service declares a
:class:`SessionKind` describing its table. Services keep their own SQL for
anything genuinely specific to the drill — how items are picked, how an answer
is graded — because that is where they actually differ.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.database import get_connection, utc_now
from backend.services import streak_service
from backend.services.errors import InvalidOperationError, ResourceNotFoundError


@dataclass(frozen=True)
class SessionKind:
    """Everything the shared lifecycle needs to know about one session table."""

    table: str
    #: Shown when the id does not exist at all.
    not_found: str
    #: Shown when the session was already submitted.
    already_ended: str
    #: Confirmation returned by :func:`complete`.
    completed: str

    # ``study_sessions`` holds two drills side by side and tells them apart with
    # a discriminator column, so the lookup has to check it. The other tables
    # are single-purpose and leave these unset.
    type_column: str | None = None
    type_value: str | None = None
    wrong_type: str = "Loại phiên học không hợp lệ cho thao tác này."


def require_open(connection: Any, kind: SessionKind, session_id: int) -> Any:
    """Return the session row, or refuse if it is missing, wrong or finished."""
    session = connection.execute(
        f"SELECT * FROM {kind.table} WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        raise ResourceNotFoundError(kind.not_found)
    if kind.type_column and session[kind.type_column] != kind.type_value:
        raise InvalidOperationError(kind.wrong_type)
    if session["ended_at"]:
        raise InvalidOperationError(kind.already_ended)
    return session


def start(kind: SessionKind, **columns: Any) -> int:
    """Insert a session row and return its id. ``started_at`` fills itself in."""
    columns.setdefault("started_at", utc_now())
    if kind.type_column and kind.type_column not in columns:
        columns[kind.type_column] = kind.type_value

    names = ", ".join(columns)
    placeholders = ", ".join("?" * len(columns))
    with get_connection() as connection:
        cursor = connection.execute(
            f"INSERT INTO {kind.table} ({names}) VALUES ({placeholders})",
            list(columns.values()),
        )
        return int(cursor.lastrowid)


def complete(
    kind: SessionKind,
    session_id: int,
    total_items: int,
    correct_items: int,
    incorrect_items: int,
    *,
    record_streak: bool = True,
) -> dict[str, Any]:
    """Close a session and stamp its totals.

    ``record_streak`` is off for the drills that already credit the streak on
    every single answer (luyện gõ, nghe chép); counting them again here would
    award the same work twice.
    """
    with get_connection() as connection:
        require_open(connection, kind, session_id)
        connection.execute(
            f"""
            UPDATE {kind.table}
            SET ended_at = ?, total_items = ?, correct_items = ?, incorrect_items = ?
            WHERE id = ?
            """,
            (utc_now(), total_items, correct_items, incorrect_items, session_id),
        )
    if record_streak:
        streak_service.record_session_result(correct_items, incorrect_items)
    return {"message": kind.completed, "session_id": session_id}


def accuracy(correct: int, incorrect: int) -> float:
    total = correct + incorrect
    return round(correct / total * 100, 1) if total else 0.0


def attempt_stats(kind: SessionKind, attempts_table: str) -> dict[str, Any]:
    """Finished-session count plus right/wrong totals from the attempts table.

    Every drill reports this same quartet on the dashboard. Sessions are counted
    only once submitted, so an abandoned session does not inflate the total.
    """
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT
                (SELECT COUNT(*) FROM {kind.table} WHERE ended_at IS NOT NULL) AS sessions,
                (SELECT COUNT(*) FROM {attempts_table} WHERE is_correct = 1) AS correct,
                (SELECT COUNT(*) FROM {attempts_table} WHERE is_correct = 0) AS incorrect
            """
        ).fetchone()
    correct = row["correct"] or 0
    incorrect = row["incorrect"] or 0
    return {
        "sessions": row["sessions"] or 0,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": accuracy(correct, incorrect),
    }
