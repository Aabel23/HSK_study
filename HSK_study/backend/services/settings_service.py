"""User preferences persisted in the local database.

Stored as a small key/value table so new preferences can be added without a
schema change. Unknown keys are rejected to keep the payload predictable.
"""

from __future__ import annotations

import json
from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError

DEFAULT_SETTINGS: dict[str, Any] = {
    "daily_goal": 20,
    "new_words_per_day": 10,
    "session_size": 20,
    "theme": "dark",
    "audio_voice": "female",
    "autoplay_audio": True,
    "show_pinyin": True,
    "show_traditional": False,
    "reduced_motion": False,
    "sound_effects": True,
    "preferred_level": "all",
}

_INT_RANGES = {
    "daily_goal": (1, 500),
    "new_words_per_day": (0, 200),
    "session_size": (5, 100),
}
_ENUMS = {
    "theme": {"dark", "light"},
    "audio_voice": {"female", "male"},
    "preferred_level": {"all", "1", "2", "3", "4", "5", "6", "7-9"},
}


def _coerce(key: str, value: Any) -> Any:
    """Validate and normalise one setting against its declared type."""
    default = DEFAULT_SETTINGS[key]
    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if isinstance(default, int):
        try:
            number = int(value)
        except (TypeError, ValueError) as error:
            raise InvalidOperationError(f"Giá trị của '{key}' phải là số nguyên.") from error
        low, high = _INT_RANGES[key]
        if not low <= number <= high:
            raise InvalidOperationError(f"'{key}' phải nằm trong khoảng {low}–{high}.")
        return number
    text = str(value)
    allowed = _ENUMS.get(key)
    if allowed and text not in allowed:
        raise InvalidOperationError(f"'{key}' không hợp lệ.")
    return text


def get_settings() -> dict[str, Any]:
    """Return every setting, falling back to the default for unset keys."""
    values = dict(DEFAULT_SETTINGS)
    with get_connection() as connection:
        rows = connection.execute("SELECT key, value FROM app_settings").fetchall()
    for row in rows:
        key = row["key"]
        if key not in DEFAULT_SETTINGS:
            continue
        try:
            values[key] = _coerce(key, json.loads(row["value"]))
        except (json.JSONDecodeError, InvalidOperationError):
            values[key] = DEFAULT_SETTINGS[key]
    return values


def get_setting(key: str) -> Any:
    return get_settings().get(key, DEFAULT_SETTINGS.get(key))


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Persist a partial settings patch and return the full merged result."""
    unknown = set(updates) - set(DEFAULT_SETTINGS)
    if unknown:
        raise InvalidOperationError(f"Cài đặt không tồn tại: {', '.join(sorted(unknown))}.")
    now = utc_now()
    coerced = {key: _coerce(key, value) for key, value in updates.items()}
    with get_connection() as connection:
        for key, value in coerced.items():
            connection.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False), now),
            )
    return get_settings()


def reset_settings() -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute("DELETE FROM app_settings")
    return dict(DEFAULT_SETTINGS)
