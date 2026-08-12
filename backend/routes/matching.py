from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import MatchingAttemptCreate, MatchingSessionCreate, SessionComplete
from backend.services import matching_service


router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.post("/session", status_code=201)
def create_matching_session(payload: MatchingSessionCreate):
    try:
        return matching_service.create_session(payload.mode.value, payload.count)
    except Exception as error:
        raise_http_error(error)


@router.post("/attempt", status_code=201)
def create_matching_attempt(payload: MatchingAttemptCreate):
    try:
        return matching_service.record_attempt(
            payload.session_id,
            payload.vocabulary_id,
            payload.mode.value,
            payload.is_correct,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_matching_session(session_id: int, payload: SessionComplete):
    try:
        return matching_service.complete_session(
            session_id,
            payload.total_items,
            payload.correct_items,
            payload.incorrect_items,
        )
    except Exception as error:
        raise_http_error(error)

