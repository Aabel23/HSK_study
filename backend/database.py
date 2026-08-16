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

CREATE TABLE IF NOT EXISTS donations (
    order_code INTEGER PRIMARY KEY,
    amount INTEGER NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    donor_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'cancelled', 'expired')),
    checkout_url TEXT,
    qr_code TEXT,
    payment_link_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    paid_at TEXT
);

CREATE TABLE IF NOT EXISTS hskk_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_level TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    answered_items INTEGER NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 0,
    max_score REAL NOT NULL DEFAULT 100
);

CREATE TABLE IF NOT EXISTS hskk_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    part INTEGER NOT NULL,
    question_index INTEGER NOT NULL,
    question_id TEXT NOT NULL DEFAULT '',
    self_rating TEXT NOT NULL CHECK (self_rating IN ('good', 'ok', 'bad', 'skipped')),
    score REAL NOT NULL DEFAULT 0,
    max_score REAL NOT NULL DEFAULT 0,
    spoken_seconds INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE (session_id, part, question_index),
    FOREIGN KEY (session_id) REFERENCES hskk_sessions(id) ON DELETE CASCADE
);

-- Grammar lessons. The content ships as scripts/data/grammar.json and is seeded
-- into `grammar_points`; `grammar_progress` is the learner's own state, kept in
-- a separate table so re-seeding new lessons never touches their history.
CREATE TABLE IF NOT EXISTS grammar_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    hsk_level TEXT NOT NULL,
    title_vi TEXT NOT NULL,
    pattern_zh TEXT NOT NULL DEFAULT '',
    summary_vi TEXT NOT NULL DEFAULT '',
    explanation_vi TEXT NOT NULL DEFAULT '',
    pitfall_vi TEXT NOT NULL DEFAULT '',
    examples_json TEXT NOT NULL DEFAULT '[]',
    exercises_json TEXT NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grammar_progress (
    grammar_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'learning', 'mastered')),
    practice_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    incorrect_count INTEGER NOT NULL DEFAULT 0,
    last_practiced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (grammar_id) REFERENCES grammar_points(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_grammar_points_level ON grammar_points(hsk_level);
CREATE INDEX IF NOT EXISTS idx_grammar_progress_status ON grammar_progress(status);

-- Which exam-bank items the learner has already been shown. The bank itself
-- ships as JSON in scripts/data/; this table is the per-machine memory that
-- lets the sampler hand out unseen questions before ever repeating one.
CREATE TABLE IF NOT EXISTS item_exposure (
    item_key TEXT PRIMARY KEY,
    seen_count INTEGER NOT NULL DEFAULT 0,
    last_seen_at TEXT NOT NULL
);

-- The character layer under the word list.
--
-- Everything else in this schema is keyed by word, which is how HSK is taught
-- and also where HSK stops: the syllabus ends and the learner is on their own.
-- A Vietnamese learner does not have to be. Over half of formal Vietnamese is
-- Sino-Vietnamese, and each character has a fixed âm Hán-Việt, so 学 = học and
-- 生 = sinh makes 学生 read as *học sinh* — a word they have always known. The
-- same pair then gives 学期 (học kỳ), 生活 (sinh hoạt), 医生 (y sinh) and on.
--
-- These tables hold that layer so the app can teach decoding rather than only
-- recall. Content ships as scripts/data/characters.json (built by
-- scripts/build_characters.py); `character_progress` is the learner's own
-- state, kept separate so re-seeding never touches their history — the same
-- split grammar_points/grammar_progress uses.
CREATE TABLE IF NOT EXISTS characters (
    hanzi TEXT PRIMARY KEY,
    pinyin TEXT NOT NULL DEFAULT '',
    han_viet TEXT NOT NULL DEFAULT '',
    -- Which source the reading came from, so a screen can say how sure it is.
    han_viet_source TEXT NOT NULL DEFAULT '',
    meaning_vi TEXT NOT NULL DEFAULT '',
    meaning_en TEXT NOT NULL DEFAULT '',
    traditional TEXT,
    stroke_count INTEGER,
    radical_number INTEGER,
    radicals_json TEXT NOT NULL DEFAULT '[]',
    mnemonic_vi TEXT NOT NULL DEFAULT '',
    stroke_hint_vi TEXT NOT NULL DEFAULT '',
    -- The lowest HSK band of any word that uses it, and how many bank words
    -- do. Both derived at seed time; they are what makes "teach me the
    -- characters that unlock the most words" a single ORDER BY.
    hsk_level TEXT,
    word_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS radicals (
    hanzi TEXT PRIMARY KEY,
    name_vi TEXT NOT NULL DEFAULT '',
    meaning_vi TEXT NOT NULL DEFAULT '',
    mnemonic_vi TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Which characters each word is made of. Denormalised on purpose: "every word
-- containing 学" is the query the word-family screen runs on every keystroke,
-- and LIKE '%学%' over 11k rows cannot use an index.
CREATE TABLE IF NOT EXISTS word_characters (
    vocabulary_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    hanzi TEXT NOT NULL,
    PRIMARY KEY (vocabulary_id, position),
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS character_progress (
    hanzi TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'learning', 'mastered')),
    seen_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    incorrect_count INTEGER NOT NULL DEFAULT 0,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    last_seen_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decode_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hsk_level TEXT NOT NULL,
    mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_items INTEGER NOT NULL DEFAULT 0,
    correct_items INTEGER NOT NULL DEFAULT 0,
    incorrect_items INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS decode_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    vocabulary_id INTEGER,
    word TEXT NOT NULL DEFAULT '',
    mode TEXT NOT NULL DEFAULT '',
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES decode_sessions(id) ON DELETE SET NULL
);

-- Example sentences for a word, gathered from material already in this repo.
--
-- Only 150 of 10.969 words shipped with an example, which is the widest gap
-- between this and a real dictionary. Rather than import a corpus whose
-- Vietnamese nobody here has read, the seeder indexes the sentences the
-- project already has and has already checked: the rearrange bank, the worked
-- examples inside each grammar lesson, and the HSKK speaking prompts. That is
-- 519 sentences, every one carrying hanzi, pinyin and a Vietnamese
-- translation, and every one written by a human for this app.
--
-- Derived rather than authored, so it is rebuilt from scratch on every seed
-- and holds nothing a learner would miss.
CREATE TABLE IF NOT EXISTS word_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    hanzi TEXT NOT NULL,
    pinyin TEXT NOT NULL DEFAULT '',
    meaning_vi TEXT NOT NULL DEFAULT '',
    -- 'sentences' | 'grammar' | 'hskk', so a screen can say where it came from.
    source TEXT NOT NULL DEFAULT '',
    source_ref TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_word_examples_vocabulary ON word_examples(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_word_characters_hanzi ON word_characters(hanzi);
CREATE INDEX IF NOT EXISTS idx_characters_level ON characters(hsk_level);
CREATE INDEX IF NOT EXISTS idx_characters_word_count ON characters(word_count DESC);
CREATE INDEX IF NOT EXISTS idx_character_progress_status ON character_progress(status);
CREATE INDEX IF NOT EXISTS idx_decode_sessions_started ON decode_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_decode_attempts_session ON decode_attempts(session_id);

CREATE INDEX IF NOT EXISTS idx_item_exposure_seen ON item_exposure(seen_count);
CREATE INDEX IF NOT EXISTS idx_hskk_sessions_started ON hskk_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_hskk_answers_session ON hskk_answers(session_id);
CREATE INDEX IF NOT EXISTS idx_donations_created ON donations(created_at);
CREATE INDEX IF NOT EXISTS idx_donations_status ON donations(status);
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
    # The word spelled out in âm Hán-Việt — 图书馆 → "đồ thư quán". Stored rather
    # than joined at read time because it is shown on the dictionary list, and
    # a three-way join per row to render one line is not worth it.
    ("han_viet", "TEXT"),
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


# The mock exam grew a written (multiple-choice) section and AI grading after
# its first release, so these columns are added in place rather than by
# recreating the tables — an installed database keeps its exam history.
HSKK_SESSION_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("quiz_session_id", "INTEGER"),
    ("written_score", "REAL NOT NULL DEFAULT 0"),
    ("written_max", "REAL NOT NULL DEFAULT 0"),
    # 'instant' shows the verdict after every question; 'deferred' withholds it
    # until the paper is submitted, the way the real exam works. Existing rows
    # default to the behaviour they were sat under.
    ("feedback_mode", "TEXT NOT NULL DEFAULT 'instant'"),
)

# A schedule for the character layer.
#
# `character_progress` shipped counting right and wrong answers and nothing
# else, which meant the decode drill had no way to come back to a reading the
# learner had just missed — it drew at random every time. Characters are the
# unit most worth scheduling here, because unlike a word a character carries
# over to vocabulary that was never studied.
CHARACTER_PROGRESS_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("ease_factor", "REAL NOT NULL DEFAULT 2.5"),
    ("interval_days", "REAL NOT NULL DEFAULT 0"),
    ("repetitions", "INTEGER NOT NULL DEFAULT 0"),
    ("lapses", "INTEGER NOT NULL DEFAULT 0"),
    ("due_at", "TEXT"),
)

HSKK_ANSWER_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("graded_by", "TEXT NOT NULL DEFAULT 'self'"),
    ("ai_score", "REAL"),
    ("ai_feedback", "TEXT"),
    ("transcript", "TEXT"),
    # What the learner actually picked, so the post-submission review can show
    # their answer next to the right one. Only meaningful for reading questions.
    ("given_answer", "TEXT NOT NULL DEFAULT ''"),
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


def _migrate_hskk_columns(connection: sqlite3.Connection) -> None:
    _add_missing_columns(connection, "hskk_sessions", HSKK_SESSION_COLUMN_MIGRATIONS)
    _add_missing_columns(connection, "hskk_answers", HSKK_ANSWER_COLUMN_MIGRATIONS)


def _migrate_character_progress_columns(connection: sqlite3.Connection) -> None:
    _add_missing_columns(
        connection, "character_progress", CHARACTER_PROGRESS_COLUMN_MIGRATIONS
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_character_progress_due ON character_progress(due_at)"
    )
    # Rows written before the schedule existed have counts but no due date.
    # Giving them one derived from the practice they already had puts them in
    # the queue straight away rather than stranding them as unscheduled.
    connection.execute(
        """
        UPDATE character_progress
        SET due_at = COALESCE(last_seen_at, created_at)
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
        _migrate_hskk_columns(connection)
        _migrate_character_progress_columns(connection)
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
