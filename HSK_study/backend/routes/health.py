"""Liveness and readiness probes."""

from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import __version__
from backend.config import get_database_path
from backend.database import get_connection
from backend.logging_config import get_logger
from backend.settings import get_settings


router = APIRouter(prefix="/api", tags=["health"])

_STARTED_AT = time.time()
_logger = get_logger("health")


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe. Intentionally does no I/O so it never fails under load."""
    return {"status": "ok", "service": "chinese-study-api", "version": __version__}


@router.get("/health/ready")
def readiness_check():
    """Readiness probe: confirms the database answers and reports row counts."""
    settings = get_settings()
    payload = {
        "status": "ok",
        "service": "chinese-study-api",
        "version": __version__,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        "database": {"path": str(get_database_path()), "connected": False},
    }
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT (SELECT COUNT(*) FROM vocabulary) AS vocabulary,
                       (SELECT COUNT(*) FROM sentences) AS sentences,
                       (SELECT COUNT(*) FROM learning_progress) AS tracked_words
                """
            ).fetchone()
        payload["database"].update(
            connected=True,
            vocabulary=row["vocabulary"],
            sentences=row["sentences"],
            tracked_words=row["tracked_words"],
        )
    except Exception as error:  # pragma: no cover - only on a broken install
        _logger.exception("Readiness check failed")
        payload["status"] = "degraded"
        payload["database"]["error"] = str(error)
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.get("/version")
def version() -> dict[str, str]:
    return {"name": "Chinese Study", "version": __version__}
