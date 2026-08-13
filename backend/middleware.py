"""ASGI middleware: request correlation, access logging, security headers, limits."""

from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.logging_config import get_logger
from backend.settings import get_settings

REQUEST_ID_HEADER = "X-Request-ID"

_logger = get_logger("http")

# Everything is locked to same-origin: the app ships its own fonts via a system
# stack and never contacts a third-party host, so no external origin is allowed.
# Inline styles stay permitted because both the React SPA and the legacy vanilla
# frontend set style attributes directly; 'unsafe-inline' for *scripts* is not
# granted, which is the part that matters for XSS.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    # The HSKK mock exam records the learner's own answer, so the microphone has
    # to be allowed for this origin — `microphone=()` made the browser refuse
    # getUserMedia before it even showed a permission prompt. Camera and location
    # stay fully blocked because nothing in the app uses them.
    "Permissions-Policy": "camera=(), microphone=(self), geolocation=(), interest-cohort=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'"
    ),
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, time the request, and log the outcome."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            _logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.1f}"
        if request.url.path.startswith("/api"):
            _logger.info(
                "%s %s -> %s",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply hardening headers to every response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.path.startswith("/api"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limit for the outbound-network audio endpoint.

    Audio synthesis is the only route that can reach the internet, so it is the
    only one worth throttling; a runaway client would otherwise hammer the TTS
    provider. Disabled by setting ``CHINESE_STUDY_AUDIO_RATE_LIMIT=0``.
    """

    def __init__(self, app, path_prefix: str = "/api/audio", window_seconds: int = 60) -> None:
        super().__init__(app)
        self.path_prefix = path_prefix
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        limit = get_settings().audio_rate_limit
        if limit <= 0 or not request.url.path.startswith(self.path_prefix):
            return await call_next(request)

        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits.setdefault(client_key, deque())
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= limit:
            retry_after = max(1, int(self.window_seconds - (now - window[0])))
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Bạn đang phát âm thanh quá nhanh. Vui lòng thử lại sau giây lát.",
                    "request_id": getattr(request.state, "request_id", None),
                },
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)
        return await call_next(request)
