from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import (
    HskkAnswerCreate,
    HskkGradeRequest,
    HskkSessionCreate,
    HskkWrittenAnswer,
)
from backend.services import gemini_service, hskk_service


router = APIRouter(prefix="/api/hskk", tags=["hskk"])


@router.get("/levels")
def list_hskk_levels():
    try:
        return hskk_service.list_levels()
    except Exception as error:
        raise_http_error(error)


@router.get("/stats")
def get_hskk_stats():
    return hskk_service.get_stats()


@router.get("/grading")
def get_grading_status():
    """Whether AI grading is available, so the UI can say so up front."""
    return {"ai_grading": gemini_service.is_configured()}


@router.post("/session", status_code=201)
def create_hskk_session(payload: HskkSessionCreate):
    try:
        return hskk_service.create_session(payload.exam_level.value)
    except Exception as error:
        raise_http_error(error)


@router.post("/written", status_code=201)
def record_hskk_written_answer(payload: HskkWrittenAnswer):
    try:
        return hskk_service.record_written_answer(
            payload.session_id,
            payload.question_index,
            payload.vocabulary_id,
            payload.is_correct,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/answer", status_code=201)
def record_hskk_answer(payload: HskkAnswerCreate):
    try:
        return hskk_service.record_answer(
            payload.session_id,
            payload.part,
            payload.question_index,
            payload.question_id,
            payload.self_rating.value,
            payload.spoken_seconds,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/grade", status_code=201)
def grade_hskk_answer(payload: HskkGradeRequest):
    try:
        return hskk_service.grade_answer(
            payload.session_id,
            payload.part,
            payload.question_index,
            payload.question_id,
            payload.audio_base64,
            payload.audio_mime_type,
            payload.spoken_seconds,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/session/{session_id}/complete")
def complete_hskk_session(session_id: int):
    try:
        return hskk_service.complete_session(session_id)
    except Exception as error:
        raise_http_error(error)
