from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import HskkAnswerCreate, HskkSessionCreate
from backend.services import hskk_service


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


@router.post("/session", status_code=201)
def create_hskk_session(payload: HskkSessionCreate):
    try:
        return hskk_service.create_session(payload.exam_level.value)
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


@router.post("/session/{session_id}/complete")
def complete_hskk_session(session_id: int):
    try:
        return hskk_service.complete_session(session_id)
    except Exception as error:
        raise_http_error(error)
