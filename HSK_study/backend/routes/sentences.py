from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import SentenceAttemptCreate, SentenceSessionCreate, SessionComplete
from backend.services import sentence_service


router = APIRouter(prefix="/api/sentences", tags=["sentences"])


@router.get("/topics")
def get_sentence_topics():
    return {"items": sentence_service.list_topics()}


@router.get("/stats")
def get_sentence_stats():
    return sentence_service.get_stats()


@router.get("/levels")
def get_sentence_levels():
    return {"items": sentence_service.list_levels()}


@router.post("/session", status_code=201)
def create_sentence_session(payload: SentenceSessionCreate):
    try:
        return sentence_service.create_session(
            payload.count,
            payload.topic,
            payload.hsk_level.value if payload.hsk_level else None,
            payload.max_tokens,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/attempt", status_code=201)
def create_sentence_attempt(payload: SentenceAttemptCreate):
    try:
        return sentence_service.record_attempt(
            payload.session_id, payload.sentence_id, payload.ordered_positions
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_sentence_session(session_id: int, payload: SessionComplete):
    try:
        return sentence_service.complete_session(
            session_id,
            payload.total_items,
            payload.correct_items,
            payload.incorrect_items,
        )
    except Exception as error:
        raise_http_error(error)

