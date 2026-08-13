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
from backend.config import ROOT_DIR


def _load_dotenv_once() -> None:
    """Read `.env` next to the project, if python-dotenv is available.

    Secrets such as the PayOS keys must never live in the source tree, so the
    donate feature is configured through the environment. Loading `.env` here
    means a developer only has to write the file once instead of exporting the
    variables in every shell. Real environment variables always win, and the
    whole thing is optional: without python-dotenv the app simply runs on
    whatever the environment already provides.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT_DIR / ".env", override=False)


_load_dotenv_once()


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

    # --- Donations (PayOS) --------------------------------------------------
    # Deliberately unset by default. The keys authorise creating payment links
    # against a real bank account and verifying webhook signatures, so they are
    # read from the environment and never committed or bundled into the .exe.
    payos_client_id: str = field(default_factory=lambda: os.getenv("PAYOS_CLIENT_ID", ""))
    payos_api_key: str = field(default_factory=lambda: os.getenv("PAYOS_API_KEY", ""))
    payos_checksum_key: str = field(
        default_factory=lambda: os.getenv("PAYOS_CHECKSUM_KEY", "")
    )
    donate_recipient: str = field(
        default_factory=lambda: os.getenv("CHINESE_STUDY_DONATE_NAME", "anh Ba")
    )
    donate_min_amount: int = field(
        default_factory=lambda: _env_int("CHINESE_STUDY_DONATE_MIN", 2_000, minimum=1_000)
    )
    donate_max_amount: int = field(
        default_factory=lambda: _env_int("CHINESE_STUDY_DONATE_MAX", 10_000_000, minimum=1_000)
    )
    donate_base_url: str = field(
        default_factory=lambda: os.getenv("CHINESE_STUDY_DONATE_BASE_URL", "").rstrip("/")
    )

    # --- AI grading (Google Gemini) -----------------------------------------
    # Used to score the spoken parts of the HSKK mock exam. Unset by default:
    # without a key the exam falls back to self-assessment, exactly like the
    # donate tab falls back when PayOS is not configured.
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    )
    gemini_timeout_seconds: int = field(
        default_factory=lambda: _env_int("GEMINI_TIMEOUT", 60, minimum=5)
    )

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def gemini_uses_bearer_token(self) -> bool:
        """Tell an API key apart from an OAuth access token.

        Google AI Studio hands out keys that start with ``AIza`` and are sent in
        the ``x-goog-api-key`` header, while tokens minted by OAuth (``ya29.``,
        ``AQ.``) must go in ``Authorization: Bearer``. Sending the wrong one
        gets a 401, so the shape of the credential picks the header.
        """
        return not self.gemini_api_key.startswith("AIza")

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"dev", "development", "local"}

    @property
    def payos_configured(self) -> bool:
        """True only when all three PayOS credentials are present."""
        return bool(self.payos_client_id and self.payos_api_key and self.payos_checksum_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached process settings."""
    return Settings()


def reset_settings_cache() -> None:
    """Drop the cached settings so tests can re-read patched environment values."""
    get_settings.cache_clear()
