"""Export and restore the learner's own data as a portable JSON document.

Vocabulary rows are *not* exported — they are reseeded from the bundled HSK
dataset. Progress is keyed by hanzi rather than row id so a backup still
restores correctly onto a database whose vocabulary ids differ.

Restore is a merge by default: existing rows are updated, missing rows inserted,
and nothing is ever deleted.
"""

from __future__ import annotations

from typing import Any

from backend import __version__
from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError

BACKUP_FORMAT = "chinese-study-backup"
BACKUP_VERSION = 1


def export_data() -> dict[str, Any]:
    """Return every user-owned table as a JSON-serialisable dictionary."""
    with get_connection() as connection:
        progress = connection.execute(
            """
            SELECT v.hanzi, p.status, p.review_count, p.correct_count, p.incorrect_count,
                   p.last_reviewed_at, p.created_at, p.updated_at,
                   COALESCE(p.ease_factor, 2.5) AS ease_factor,
                   COALESCE(p.interval_days, 0) AS interval_days,
                   COALESCE(p.repetitions, 0) AS repetitions,
                   COALESCE(p.lapses, 0) AS lapses,
                   p.due_at, COALESCE(p.is_favorite, 0) AS is_favorite, p.note
            FROM learning_progress p
            JOIN vocabulary v ON v.id = p.vocabulary_id
            -- Seeding creates an untouched row per word; exporting those would
            -- bloat the backup with tens of thousands of no-op entries.
            WHERE p.status != 'new'
               OR COALESCE(p.review_count, 0) > 0
               OR COALESCE(p.is_favorite, 0) = 1
               OR p.note IS NOT NULL
               OR p.due_at IS NOT NULL
            """
        ).fetchall()
        writing = connection.execute("SELECT * FROM writing_progress").fetchall()
        activity = connection.execute("SELECT * FROM daily_activity").fetchall()
        settings = connection.execute("SELECT key, value, updated_at FROM app_settings").fetchall()
        achievements = connection.execute("SELECT code, unlocked_at FROM achievements").fetchall()

    return {
        "format": BACKUP_FORMAT,
        "backup_version": BACKUP_VERSION,
        "app_version": __version__,
        "exported_at": utc_now(),
        "learning_progress": [dict(row) for row in progress],
        "writing_progress": [
            {key: value for key, value in dict(row).items() if key != "id"} for row in writing
        ],
        "daily_activity": [dict(row) for row in activity],
        "app_settings": [dict(row) for row in settings],
        "achievements": [dict(row) for row in achievements],
    }


def _validate(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise InvalidOperationError("Tệp sao lưu không hợp lệ.")
    if payload.get("format") != BACKUP_FORMAT:
        raise InvalidOperationError("Tệp này không phải bản sao lưu của Chinese Study.")
    if int(payload.get("backup_version", 0)) > BACKUP_VERSION:
        raise InvalidOperationError(
            "Bản sao lưu được tạo bởi phiên bản mới hơn. Hãy cập nhật ứng dụng trước."
        )


def import_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge a backup into the current database. Never deletes existing rows."""
    _validate(payload)
    now = utc_now()
    counters = {
        "learning_progress": 0,
        "writing_progress": 0,
        "daily_activity": 0,
        "app_settings": 0,
        "achievements": 0,
        "skipped_unknown_words": 0,
    }

    with get_connection() as connection:
        vocabulary_ids = {
            row["hanzi"]: row["id"]
            for row in connection.execute("SELECT id, hanzi FROM vocabulary")
        }

        for row in payload.get("learning_progress", []) or []:
            vocabulary_id = vocabulary_ids.get(row.get("hanzi"))
            if vocabulary_id is None:
                counters["skipped_unknown_words"] += 1
                continue
            connection.execute(
                """
                INSERT INTO learning_progress (
                    vocabulary_id, status, review_count, correct_count, incorrect_count,
                    last_reviewed_at, created_at, updated_at, ease_factor, interval_days,
                    repetitions, lapses, due_at, is_favorite, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vocabulary_id) DO UPDATE SET
                    status = excluded.status,
                    review_count = MAX(learning_progress.review_count, excluded.review_count),
                    correct_count = MAX(learning_progress.correct_count, excluded.correct_count),
                    incorrect_count = MAX(learning_progress.incorrect_count, excluded.incorrect_count),
                    last_reviewed_at = COALESCE(excluded.last_reviewed_at, learning_progress.last_reviewed_at),
                    updated_at = excluded.updated_at,
                    ease_factor = excluded.ease_factor,
                    interval_days = excluded.interval_days,
                    repetitions = excluded.repetitions,
                    lapses = excluded.lapses,
                    due_at = COALESCE(excluded.due_at, learning_progress.due_at),
                    is_favorite = excluded.is_favorite,
                    note = COALESCE(excluded.note, learning_progress.note)
                """,
                (
                    vocabulary_id,
                    row.get("status", "new"),
                    int(row.get("review_count") or 0),
                    int(row.get("correct_count") or 0),
                    int(row.get("incorrect_count") or 0),
                    row.get("last_reviewed_at"),
                    row.get("created_at") or now,
                    now,
                    float(row.get("ease_factor") or 2.5),
                    float(row.get("interval_days") or 0),
                    int(row.get("repetitions") or 0),
                    int(row.get("lapses") or 0),
                    row.get("due_at"),
                    1 if row.get("is_favorite") else 0,
                    row.get("note"),
                ),
            )
            counters["learning_progress"] += 1

        for row in payload.get("writing_progress", []) or []:
            character = row.get("character")
            if not character:
                continue
            connection.execute(
                """
                INSERT INTO writing_progress (
                    character, status, practice_count, success_count,
                    last_practiced_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(character) DO UPDATE SET
                    status = excluded.status,
                    practice_count = MAX(writing_progress.practice_count, excluded.practice_count),
                    success_count = MAX(writing_progress.success_count, excluded.success_count),
                    last_practiced_at = COALESCE(excluded.last_practiced_at, writing_progress.last_practiced_at),
                    updated_at = excluded.updated_at
                """,
                (
                    character,
                    row.get("status", "new"),
                    int(row.get("practice_count") or 0),
                    int(row.get("success_count") or 0),
                    row.get("last_practiced_at"),
                    row.get("created_at") or now,
                    now,
                ),
            )
            counters["writing_progress"] += 1

        for row in payload.get("daily_activity", []) or []:
            activity_date = row.get("activity_date")
            if not activity_date:
                continue
            connection.execute(
                """
                INSERT INTO daily_activity (
                    activity_date, reviews_done, correct_count, incorrect_count,
                    new_learned, study_seconds, xp, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(activity_date) DO UPDATE SET
                    reviews_done = MAX(daily_activity.reviews_done, excluded.reviews_done),
                    correct_count = MAX(daily_activity.correct_count, excluded.correct_count),
                    incorrect_count = MAX(daily_activity.incorrect_count, excluded.incorrect_count),
                    new_learned = MAX(daily_activity.new_learned, excluded.new_learned),
                    study_seconds = MAX(daily_activity.study_seconds, excluded.study_seconds),
                    xp = MAX(daily_activity.xp, excluded.xp),
                    updated_at = excluded.updated_at
                """,
                (
                    activity_date,
                    int(row.get("reviews_done") or 0),
                    int(row.get("correct_count") or 0),
                    int(row.get("incorrect_count") or 0),
                    int(row.get("new_learned") or 0),
                    int(row.get("study_seconds") or 0),
                    int(row.get("xp") or 0),
                    row.get("created_at") or now,
                    now,
                ),
            )
            counters["daily_activity"] += 1

        for row in payload.get("app_settings", []) or []:
            key = row.get("key")
            if not key:
                continue
            connection.execute(
                """
                INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, row.get("value", "null"), now),
            )
            counters["app_settings"] += 1

        for row in payload.get("achievements", []) or []:
            code = row.get("code")
            if not code:
                continue
            connection.execute(
                "INSERT OR IGNORE INTO achievements (code, unlocked_at) VALUES (?, ?)",
                (code, row.get("unlocked_at") or now),
            )
            counters["achievements"] += 1

    return {"imported": counters, "restored_at": now}
