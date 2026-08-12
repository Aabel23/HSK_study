"""Dictation endpoints: listen, then write down what you heard."""

from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import (
    DictationAnswerCheck,
    DictationSessionCreate,
    SessionComplete,
)
from backend.services import dictation_service


router = APIRouter(prefix="/api/dictation", tags=["dictation"])


@router.get("/modes")
def get_modes():
    return {
        "items": [{"mode": mode, "label": label} for mode, label in dictation_service.MODES.items()]
    }


@router.get("/stats")
def get_stats():
    return dictation_service.get_stats()


@router.post("/session", status_code=201)
def create_dictation_session(payload: DictationSessionCreate):
    try:
        return dictation_service.create_session(
            payload.hsk_level.value if payload.hsk_level else None,
            payload.mode.value,
            payload.count,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/check")
def check_dictation_answer(payload: DictationAnswerCheck):
    try:
        return dictation_service.check_answer(
            payload.session_id,
            payload.target_id,
            payload.mode.value,
            payload.answer,
            payload.replays,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_dictation_session(session_id: int, payload: SessionComplete):
    try:
        return dictation_service.complete_session(
            session_id, payload.total_items, payload.correct_items, payload.incorrect_items
        )
    except Exception as error:
        raise_http_error(error)
