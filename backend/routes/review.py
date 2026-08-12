"""Spaced-repetition review queue endpoints."""

from fastapi import APIRouter, Query

from backend.routes.utils import raise_http_error
from backend.schemas import FavoriteUpdate, HskLevel, NoteUpdate, ReviewSubmit
from backend.services import srs_service


router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/queue")
def get_queue(
    limit: int = Query(default=20, ge=1, le=100),
    hsk_level: HskLevel | None = None,
    include_new: bool = True,
    new_limit: int | None = Query(default=None, ge=0, le=100),
):
    return srs_service.get_due_queue(
        limit=limit,
        hsk_level=hsk_level.value if hsk_level else None,
        include_new=include_new,
        new_limit=new_limit,
    )


@router.get("/stats")
def get_stats():
    return srs_service.get_stats()


@router.get("/forecast")
def get_forecast(days: int = Query(default=14, ge=1, le=60)):
    return {"items": srs_service.get_forecast(days)}


@router.post("/submit")
def submit_review(payload: ReviewSubmit):
    try:
        return srs_service.submit_review(
            payload.vocabulary_id, payload.rating.value, payload.source
        )
    except Exception as error:
        raise_http_error(error)


@router.get("/favorites")
def list_favorites(limit: int = Query(default=200, ge=1, le=500)):
    return {"items": srs_service.list_favorites(limit)}


@router.post("/favorite")
def set_favorite(payload: FavoriteUpdate):
    try:
        return srs_service.set_favorite(payload.vocabulary_id, payload.is_favorite)
    except Exception as error:
        raise_http_error(error)


@router.post("/note")
def set_note(payload: NoteUpdate):
    try:
        return srs_service.set_note(payload.vocabulary_id, payload.note)
    except Exception as error:
        raise_http_error(error)
