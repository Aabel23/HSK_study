"""Typing practice endpoints (produce the word, don't just recognise it)."""

from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import (
    SessionComplete,
    TypingAnswerCheck,
    TypingSessionCreate,
)
from backend.services import typing_service


router = APIRouter(prefix="/api/typing", tags=["typing"])


@router.get("/modes")
def get_modes():
    return {"items": [{"mode": mode, "label": label} for mode, label in typing_service.MODES.items()]}


@router.get("/stats")
def get_stats():
    return typing_service.get_stats()


@router.post("/session", status_code=201)
def create_typing_session(payload: TypingSessionCreate):
    try:
        return typing_service.create_session(
            payload.hsk_level.value if payload.hsk_level else None,
            payload.mode.value,
            payload.count,
            payload.only_due,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/check")
def check_typing_answer(payload: TypingAnswerCheck):
    try:
        return typing_service.check_answer(
            payload.session_id, payload.vocabulary_id, payload.mode.value, payload.answer
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_typing_session(session_id: int, payload: SessionComplete):
    try:
        return typing_service.complete_session(
            session_id, payload.total_items, payload.correct_items, payload.incorrect_items
        )
    except Exception as error:
        raise_http_error(error)
