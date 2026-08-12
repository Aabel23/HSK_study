"""Application logging setup.

Emits human-readable lines by default and single-line JSON when
``CHINESE_STUDY_LOG_JSON=1``, so the same build works for a desktop user reading
the console and for a log collector parsing stdout.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from backend.config import DEFAULT_DATABASE_PATH, IS_FROZEN
from backend.settings import get_settings

LOGGER_NAME = "chinese_study"

_RESERVED_RECORD_KEYS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message", "module",
        "msecs", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Render records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Compact console format with the request id appended when present."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        request_id = getattr(record, "request_id", None)
        return f"{base} [req={request_id}]" if request_id else base


def _log_file_path() -> Path | None:
    """Where the packaged app writes its rolling log, or None when running from source."""
    if not IS_FROZEN:
        return None
    log_dir = DEFAULT_DATABASE_PATH.parent / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return log_dir / "chinese-study.log"


def configure_logging() -> logging.Logger:
    """Install the root handlers once and return the application logger."""
    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)
    formatter = JsonFormatter() if settings.log_json else ConsoleFormatter()

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)

    # A windowed (--noconsole) PyInstaller build has no stdout at all, so the
    # stream handler is only attached when there is somewhere to write.
    if sys.stdout is not None:
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    # The packaged app also logs to disk: without it, a user reporting a crash
    # would have nothing to send.
    log_file = _log_file_path()
    if log_file is not None:
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            pass

    if not root.handlers:
        root.addHandler(logging.NullHandler())
    root.setLevel(level)

    # uvicorn installs its own handlers; route them through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    logging.getLogger("uvicorn.access").setLevel(
        logging.INFO if settings.is_development else logging.WARNING
    )
    return get_logger()


def get_logger(suffix: str | None = None) -> logging.Logger:
    """Return the shared application logger, optionally namespaced."""
    return logging.getLogger(f"{LOGGER_NAME}.{suffix}" if suffix else LOGGER_NAME)
