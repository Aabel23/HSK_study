from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import ListeningAttemptCreate, ListeningSessionCreate, SessionComplete
from backend.services import listening_service


router = APIRouter(prefix="/api/listening", tags=["listening"])


@router.get("/stats")
def get_listening_stats():
    return listening_service.get_stats()


@router.post("/session", status_code=201)
def create_listening_session(payload: ListeningSessionCreate):
    try:
        return listening_service.create_session(
            payload.hsk_level.value if payload.hsk_level else None,
            payload.mode.value,
            payload.count,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/attempt", status_code=201)
def create_listening_attempt(payload: ListeningAttemptCreate):
    try:
        return listening_service.record_attempt(
            payload.session_id, payload.vocabulary_id, payload.mode.value, payload.is_correct
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_listening_session(session_id: int, payload: SessionComplete):
    try:
        return listening_service.complete_session(
            session_id, payload.total_items, payload.correct_items, payload.incorrect_items
        )
    except Exception as error:
        raise_http_error(error)
