from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import SessionComplete, WritingAttemptCreate, WritingSessionCreate
from backend.services import writing_service


router = APIRouter(prefix="/api/writing", tags=["writing"])


@router.get("/progress")
def get_writing_progress():
    return writing_service.get_progress_summary()


@router.post("/session", status_code=201)
def create_writing_session(payload: WritingSessionCreate):
    try:
        return writing_service.create_session(
            payload.hsk_level.value if payload.hsk_level else None, payload.count
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/attempt", status_code=201)
def create_writing_attempt(payload: WritingAttemptCreate):
    try:
        return writing_service.record_attempt(
            payload.session_id, payload.character, payload.mistakes, payload.is_correct
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_writing_session(session_id: int, payload: SessionComplete):
    try:
        return writing_service.complete_session(
            session_id, payload.total_items, payload.correct_items, payload.incorrect_items
        )
    except Exception as error:
        raise_http_error(error)
