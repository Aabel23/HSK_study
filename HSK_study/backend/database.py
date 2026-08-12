"""SQLite connection and schema management."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from backend.config import get_database_path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hanzi TEXT NOT NULL UNIQUE,
    pinyin TEXT NOT NULL,
    meaning TEXT NOT NULL,
    example TEXT,
    example_pinyin TEXT,
    example_meaning TEXT,
    topic TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'learning', 'review', 'mastered')),
    review_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    incorrect_count INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type TEXT NOT NULL
        CHECK (session_type IN ('flashcard', 'matching')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS matching_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    vocabulary_id INTEGER NOT NULL,
    matching_mode TEXT NOT NULL
        CHECK (matching_mode IN ('meaning', 'pinyin')),
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sentences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hanzi TEXT NOT NULL UNIQUE,
    pinyin TEXT NOT NULL,
    meaning TEXT NOT NULL,
    topic TEXT,
    tokens_json TEXT NOT NULL,
    pinyin_tokens_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sentence_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sentence_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    sentence_id INTEGER NOT NULL,
    ordered_positions_json TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sentence_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vocabulary_topic ON vocabulary(topic);
CREATE INDEX IF NOT EXISTS idx_progress_status ON learning_progress(status);
CREATE INDEX IF NOT EXISTS idx_progress_last_reviewed ON learning_progress(last_reviewed_at);
CREATE INDEX IF NOT EXISTS idx_sessions_type_started ON study_sessions(session_type, started_at);
CREATE INDEX IF NOT EXISTS idx_matching_attempts_session ON matching_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_sentences_topic ON sentences(topic);
CREATE INDEX IF NOT EXISTS idx_sentence_sessions_started ON sentence_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sentence_attempts_session ON sentence_attempts(session_id);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hsk_level TEXT NOT NULL
        CHECK (hsk_level IN ('1', '2', '3', '4', '5', '6', '7-9', 'all')),
    question_types_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    vocabulary_id INTEGER NOT NULL,
    question_type TEXT NOT NULL
        CHECK (question_type IN ('mcq_meaning', 'mcq_hanzi', 'mcq_pinyin', 'mcq_audio')),
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS listening_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hsk_level TEXT NOT NULL
        CHECK (hsk_level IN ('1', '2', '3', '4', '5', '6', '7-9', 'all')),
    mode TEXT NOT NULL CHECK (mode IN ('audio_to_meaning', 'audio_to_hanzi')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS listening_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    vocabulary_id INTEGER NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('audio_to_meaning', 'audio_to_hanzi')),
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES listening_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS writing_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hsk_level TEXT NOT NULL
        CHECK (hsk_level IN ('1', '2', '3', '4', '5', '6', '7-9', 'all')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS writing_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    character TEXT NOT NULL,
    mistakes INTEGER NOT NULL DEFAULT 0,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES writing_sessions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS writing_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'learning', 'mastered')),
    practice_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    last_practiced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_started ON quiz_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_session ON quiz_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_listening_sessions_started ON listening_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_listening_attempts_session ON listening_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_writing_sessions_started ON writing_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_writing_attempts_session ON writing_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_writing_progress_status ON writing_progress(status);
"""

# Tables introduced with the spaced-repetition, streak and achievement features.
# Kept in a separate script so the original schema above stays untouched.
SCHEMA_SQL_EXTENSIONS = """
CREATE TABLE IF NOT EXISTS daily_activity (
    activity_date TEXT PRIMARY KEY,
    reviews_done INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    incorrect_count INTEGER NOT NULL DEFAULT 0,
    new_learned INTEGER NOT NULL DEFAULT 0,
    study_seconds INTEGER NOT NULL DEFAULT 0,
    xp INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('again', 'hard', 'good', 'easy')),
    previous_interval REAL NOT NULL DEFAULT 0,
    next_interval REAL NOT NULL DEFAULT 0,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    source TEXT NOT NULL DEFAULT 'review',
    created_at TEXT NOT NULL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS achievements (
    code TEXT PRIMARY KEY,
    unlocked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS typing_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hsk_level TEXT NOT NULL,
    mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS typing_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    vocabulary_id INTEGER NOT NULL,
    mode TEXT NOT NULL,
    answer TEXT NOT NULL DEFAULT '',
    expected TEXT NOT NULL DEFAULT '',
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES typing_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dictation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hsk_level TEXT NOT NULL,
    mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dictation_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    vocabulary_id INTEGER,
    sentence_id INTEGER,
    mode TEXT NOT NULL,
    answer TEXT NOT NULL DEFAULT '',
    expected TEXT NOT NULL DEFAULT '',
    replays INTEGER NOT NULL DEFAULT 0,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES dictation_sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_daily_activity_date ON daily_activity(activity_date);
CREATE INDEX IF NOT EXISTS idx_review_log_created ON review_log(created_at);
CREATE INDEX IF NOT EXISTS idx_review_log_vocabulary ON review_log(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_typing_attempts_session ON typing_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_dictation_attempts_session ON dictation_attempts(session_id);
"""

# Level tagging for sentences, added so the rearrange exercise can follow the
# HSK level picker instead of always drawing from the original HSK1 set.
SENTENCE_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("hsk_level", "TEXT NOT NULL DEFAULT '1'"),
    ("difficulty", "INTEGER NOT NULL DEFAULT 0"),
)

# Columns added after the original release. Kept additive via ALTER TABLE so
# existing databases upgrade in place without losing data (see AGENTS.md).
VOCABULARY_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("hsk_level", "TEXT NOT NULL DEFAULT '1'"),
    ("meaning_en", "TEXT"),
    ("traditional", "TEXT"),
    ("pos", "TEXT"),
    ("pos_vi", "TEXT"),
    ("classifiers", "TEXT"),
    ("frequency", "INTEGER"),
)


# Spaced-repetition, bookmark and note columns added on top of the original
# progress table. Same additive ALTER TABLE strategy as the vocabulary columns.
PROGRESS_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("ease_factor", "REAL NOT NULL DEFAULT 2.5"),
    ("interval_days", "REAL NOT NULL DEFAULT 0"),
    ("repetitions", "INTEGER NOT NULL DEFAULT 0"),
    ("lapses", "INTEGER NOT NULL DEFAULT 0"),
    ("due_at", "TEXT"),
    ("is_favorite", "INTEGER NOT NULL DEFAULT 0"),
    ("note", "TEXT"),
)


def _add_missing_columns(
    connection: sqlite3.Connection,
    table: str,
    migrations: tuple[tuple[str, str], ...],
) -> None:
    """Add any column in ``migrations`` that the table does not already have."""
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    for column_name, column_definition in migrations:
        if column_name not in existing:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column_name} {column_definition}"
            )


def _migrate_vocabulary_columns(connection: sqlite3.Connection) -> None:
    _add_missing_columns(connection, "vocabulary", VOCABULARY_COLUMN_MIGRATIONS)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_vocabulary_hsk_level ON vocabulary(hsk_level)"
    )


def _migrate_sentence_columns(connection: sqlite3.Connection) -> None:
    _add_missing_columns(connection, "sentences", SENTENCE_COLUMN_MIGRATIONS)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sentences_hsk_level ON sentences(hsk_level)"
    )
    # Difficulty is simply the token count, which is what makes a rearrange
    # exercise hard. Backfilled for rows written before the column existed.
    connection.execute(
        """
        UPDATE sentences
        SET difficulty = LENGTH(tokens_json) - LENGTH(REPLACE(tokens_json, ',', '')) + 1
        WHERE difficulty = 0
        """
    )


def _migrate_progress_columns(connection: sqlite3.Connection) -> None:
    _add_missing_columns(connection, "learning_progress", PROGRESS_COLUMN_MIGRATIONS)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_progress_due_at ON learning_progress(due_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_progress_favorite ON learning_progress(is_favorite)"
    )
    # Rows written before the SRS feature have no schedule. Give them one derived
    # from the review they already had so they surface in the queue immediately.
    connection.execute(
        """
        UPDATE learning_progress
        SET due_at = COALESCE(last_reviewed_at, created_at)
        WHERE due_at IS NULL AND status != 'new'
        """
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize_database(database_path: str | Path | None = None) -> Path:
    path = Path(database_path) if database_path else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_SQL)
        connection.executescript(SCHEMA_SQL_EXTENSIONS)
        _migrate_vocabulary_columns(connection)
        _migrate_progress_columns(connection)
        _migrate_sentence_columns(connection)
        connection.commit()
    finally:
        connection.close()
    return path


@contextmanager
def get_connection(database_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(database_path) if database_path else get_database_path()
    if not path.exists():
        initialize_database(path)
    connection = sqlite3.connect(path, timeout=15.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
