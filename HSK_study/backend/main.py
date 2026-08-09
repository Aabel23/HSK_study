"""FastAPI application that serves both the API and vanilla frontend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR, WEB_DIST_DIR
from backend.database import initialize_database
from backend.routes import (
    audio,
    dashboard,
    flashcard,
    health,
    listening,
    matching,
    progress,
    quiz,
    sentences,
    vocabulary,
    writing,
)
from scripts.seed_data import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    seed_database()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Chinese Study API",
        description="API học từ vựng HSK cho người Việt.",
        version="2.0.0",
        lifespan=lifespan,
    )
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
    application.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

    @application.get("/legacy", include_in_schema=False)
    def legacy_frontend_shell():
        return FileResponse(FRONTEND_DIR / "index.html")

    if WEB_DIST_DIR.exists():
        application.mount("/", StaticFiles(directory=WEB_DIST_DIR, html=True), name="web")
    else:
        @application.get("/", include_in_schema=False)
        def frontend_not_built():
            return RedirectResponse("/legacy")

    return application


app = create_app()
