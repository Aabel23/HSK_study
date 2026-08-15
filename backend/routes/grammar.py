from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import GrammarExerciseCheck, GrammarStatus, HskLevel
from backend.services import grammar_service


router = APIRouter(prefix="/api/grammar", tags=["grammar"])


@router.get("/stats")
def get_grammar_stats():
    return grammar_service.get_stats()


@router.get("/points")
def list_grammar_points(
    hsk_level: HskLevel | None = None, status: GrammarStatus | None = None
):
    return grammar_service.list_points(
        hsk_level.value if hsk_level else None,
        status.value if status else None,
    )


@router.get("/points/{code}")
def get_grammar_point(code: str):
    try:
        return grammar_service.get_point(code)
    except Exception as error:
        raise_http_error(error)


@router.post("/points/{code}/check")
def check_grammar_exercise(code: str, payload: GrammarExerciseCheck):
    try:
        return grammar_service.check_exercise(code, payload.index, payload.answer)
    except Exception as error:
        raise_http_error(error)
