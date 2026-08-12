"""Application paths and shared constants."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", ROOT_DIR))
WEB_DIST_DIR = (BUNDLE_DIR if IS_FROZEN else ROOT_DIR) / "frontend-web" / "dist"


def _default_database_path() -> Path:
    if not IS_FROZEN:
        return ROOT_DIR / "data" / "chinese_study.db"
    local_app_data = os.getenv("LOCALAPPDATA")
    data_root = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return data_root / "ChineseStudy" / "chinese_study.db"


DEFAULT_DATABASE_PATH = _default_database_path()


def _default_audio_cache_dir() -> Path:
    if not IS_FROZEN:
        return ROOT_DIR / "data" / "audio_cache"
    local_app_data = os.getenv("LOCALAPPDATA")
    data_root = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return data_root / "ChineseStudy" / "audio_cache"


DEFAULT_AUDIO_CACHE_DIR = _default_audio_cache_dir()

VALID_PROGRESS_STATUSES = {"new", "learning", "review", "mastered"}
VALID_FLASHCARD_RESULTS = {"forgot", "hard", "remembered"}
VALID_MATCHING_MODES = {"meaning", "pinyin"}
VALID_SESSION_TYPES = {"flashcard", "matching"}
VALID_HSK_LEVELS = {"1", "2", "3", "4", "5", "6", "7-9"}


def get_database_path() -> Path:
    """Return the SQLite path for source, packaged app, or isolated tests."""
    configured_path = os.getenv("CHINESE_STUDY_DB")
    return Path(configured_path).resolve() if configured_path else DEFAULT_DATABASE_PATH


def get_audio_cache_dir() -> Path:
    """Return the directory used to cache generated pronunciation audio."""
    configured_path = os.getenv("CHINESE_STUDY_AUDIO_DIR")
    path = Path(configured_path).resolve() if configured_path else DEFAULT_AUDIO_CACHE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path
