from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import QuizAttemptCreate, QuizSessionCreate, SessionComplete
from backend.services import quiz_service


router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.get("/stats")
def get_quiz_stats():
    return quiz_service.get_stats()


@router.post("/session", status_code=201)
def create_quiz_session(payload: QuizSessionCreate):
    try:
        return quiz_service.create_session(
            payload.hsk_level.value if payload.hsk_level else None,
            [item.value for item in payload.question_types],
            payload.count,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/attempt", status_code=201)
def create_quiz_attempt(payload: QuizAttemptCreate):
    try:
        return quiz_service.record_attempt(
            payload.session_id,
            payload.vocabulary_id,
            payload.question_type.value,
            payload.is_correct,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_quiz_session(session_id: int, payload: SessionComplete):
    try:
        return quiz_service.complete_session(
            session_id, payload.total_items, payload.correct_items, payload.incorrect_items
        )
    except Exception as error:
        raise_http_error(error)
