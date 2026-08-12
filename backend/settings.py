"""Runtime settings resolved from environment variables.

Paths stay in :mod:`backend.config` for backwards compatibility; this module only
adds the operational knobs a production deployment needs (logging, CORS, limits).
Every value has a safe local-first default so the packaged desktop build keeps
working with no environment configured at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from backend import __version__


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return minimum
    return value


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return list(default)
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or list(default)


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the process configuration."""

    version: str = __version__
    environment: str = field(
        default_factory=lambda: os.getenv("CHINESE_STUDY_ENV", "production")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("CHINESE_STUDY_LOG_LEVEL", "INFO").upper()
    )
    log_json: bool = field(default_factory=lambda: _env_bool("CHINESE_STUDY_LOG_JSON", False))
    host: str = field(default_factory=lambda: os.getenv("CHINESE_STUDY_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("CHINESE_STUDY_PORT", 8000, minimum=1))
    cors_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "CHINESE_STUDY_CORS_ORIGINS",
            ["http://127.0.0.1:5173", "http://localhost:5173"],
        )
    )
    docs_enabled: bool = field(default_factory=lambda: _env_bool("CHINESE_STUDY_DOCS", True))
    seed_on_startup: bool = field(default_factory=lambda: _env_bool("CHINESE_STUDY_SEED", True))
    audio_rate_limit: int = field(
        default_factory=lambda: _env_int("CHINESE_STUDY_AUDIO_RATE_LIMIT", 240, minimum=0)
    )
    request_timeout_seconds: int = field(
        default_factory=lambda: _env_int("CHINESE_STUDY_REQUEST_TIMEOUT", 60, minimum=1)
    )
    open_browser: bool = field(
        default_factory=lambda: not _env_bool("CHINESE_STUDY_NO_BROWSER", False)
    )

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"dev", "development", "local"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached process settings."""
    return Settings()


def reset_settings_cache() -> None:
    """Drop the cached settings so tests can re-read patched environment values."""
    get_settings.cache_clear()
