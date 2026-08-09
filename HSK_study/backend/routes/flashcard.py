from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import FlashcardReviewCreate, FlashcardSessionCreate, SessionComplete
from backend.services import flashcard_service


router = APIRouter(prefix="/api/flashcard", tags=["flashcard"])


@router.post("/session", status_code=201)
def create_flashcard_session(payload: FlashcardSessionCreate):
    try:
        return flashcard_service.create_session(payload.count, payload.include_mastered)
    except Exception as error:
        raise_http_error(error)


@router.post("/review")
def review_flashcard(payload: FlashcardReviewCreate):
    try:
        return flashcard_service.review_card(
            payload.session_id, payload.vocabulary_id, payload.result.value
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_flashcard_session(session_id: int, payload: SessionComplete):
    try:
        return flashcard_service.complete_session(
            session_id,
            payload.total_items,
            payload.correct_items,
            payload.incorrect_items,
        )
    except Exception as error:
        raise_http_error(error)

