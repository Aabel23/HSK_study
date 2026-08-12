"""FastAPI application that serves the API and the React SPA."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend import __version__
from backend.config import WEB_DIST_DIR
from backend.database import initialize_database
from backend.logging_config import configure_logging, get_logger
from backend.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from backend.routes import (
    audio,
    backup,
    dashboard,
    dictation,
    donate,
    flashcard,
    health,
    listening,
    matching,
    progress,
    quiz,
    review,
    sentences,
    settings as settings_routes,
    streak,
    typing,
    vocabulary,
    writing,
)
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.settings import get_settings
from scripts.seed_data import seed_database

logger = get_logger("app")

STARTED_AT = time.time()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging()
    logger.info(
        "Starting Chinese Study %s (%s)",
        __version__,
        settings.environment,
        extra={"version": __version__, "environment": settings.environment},
    )
    initialize_database()
    if settings.seed_on_startup:
        seed_database()
    logger.info("Database ready")
    yield
    logger.info("Chinese Study stopped")


def _error_response(request: Request, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


def _register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(ResourceNotFoundError)
    async def _not_found(request: Request, error: ResourceNotFoundError):
        return _error_response(request, 404, str(error))

    @application.exception_handler(InvalidOperationError)
    async def _invalid(request: Request, error: InvalidOperationError):
        return _error_response(request, 409, str(error))

    @application.exception_handler(RequestValidationError)
    async def _validation(request: Request, error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Dữ liệu gửi lên không hợp lệ.",
                "errors": error.errors(),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def _http(request: Request, error: StarletteHTTPException):
        return _error_response(request, error.status_code, str(error.detail))

    @application.exception_handler(Exception)
    async def _unhandled(request: Request, error: Exception):
        # The request id is echoed back so a user-reported failure can be traced
        # to the matching stack trace in the log.
        logger.exception(
            "Unhandled error on %s %s",
            request.method,
            request.url.path,
            extra={"request_id": getattr(request.state, "request_id", None)},
        )
        return _error_response(
            request, 500, "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại."
        )


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Chinese Study API",
        description="API học tiếng Trung HSK 1-9 cho người Việt.",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.docs_enabled else None,
        redoc_url="/api/redoc" if settings.docs_enabled else None,
        openapi_url="/api/openapi.json" if settings.docs_enabled else None,
    )

    # Middleware runs bottom-up, so security headers are applied last and the
    # request id is assigned first.
    application.add_middleware(GZipMiddleware, minimum_size=1024)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    _register_exception_handlers(application)

    application.include_router(health.router)
    application.include_router(vocabulary.router)
    application.include_router(progress.router)
    application.include_router(flashcard.router)
    application.include_router(matching.router)
    application.include_router(sentences.router)
    application.include_router(quiz.router)
    application.include_router(listening.router)
    application.include_router(writing.router)
    application.include_router(audio.router)
    application.include_router(dashboard.router)
    application.include_router(review.router)
    application.include_router(streak.router)
    application.include_router(settings_routes.router)
    application.include_router(backup.router)
    application.include_router(typing.router)
    application.include_router(dictation.router)
    application.include_router(donate.router)

    if WEB_DIST_DIR.exists():
        application.mount("/", StaticFiles(directory=WEB_DIST_DIR, html=True), name="web")
    else:
        @application.get("/", include_in_schema=False)
        def frontend_not_built():
            return JSONResponse(
                {"detail": "frontend-web chưa được build. Chạy 'npm run build' trong frontend-web/."},
                status_code=503,
            )

    return application


app = create_app()
