from fastapi import APIRouter, Query

from backend.routes.utils import raise_http_error
from backend.schemas import (
    CharacterStatusUpdate,
    DecodeAttemptCreate,
    DecodeSessionCreate,
    SessionComplete,
)
from backend.services import character_service


router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("")
def list_characters(
    search: str | None = None,
    hsk_level: str | None = None,
    limit: int = Query(default=40, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: str = "reach",
    in_bank_only: bool = True,
):
    try:
        return character_service.list_characters(
            search=search,
            hsk_level=hsk_level,
            limit=limit,
            offset=offset,
            sort=sort,
            in_bank_only=in_bank_only,
        )
    except Exception as error:
        raise_http_error(error)


@router.get("/stats")
def character_stats():
    try:
        return character_service.stats()
    except Exception as error:
        raise_http_error(error)


@router.get("/drill/stats")
def decode_stats():
    try:
        return character_service.drill_stats()
    except Exception as error:
        raise_http_error(error)


@router.get("/modes")
def decode_modes():
    return {
        "items": [
            {"value": value, "label": label}
            for value, label in character_service.MODES.items()
        ]
    }


@router.post("/drill/session", status_code=201)
def create_decode_session(payload: DecodeSessionCreate):
    try:
        return character_service.create_session(
            payload.mode,
            payload.count,
            hsk_level=payload.hsk_level.value if payload.hsk_level else None,
        )
    except Exception as error:
        raise_http_error(error)


@router.get("/drill/session/{session_id}/next")
def next_decode_question(session_id: int):
    try:
        return character_service.next_question(session_id)
    except Exception as error:
        raise_http_error(error)


@router.post("/drill/attempt", status_code=201)
def create_decode_attempt(payload: DecodeAttemptCreate):
    try:
        return character_service.record_attempt(
            payload.session_id,
            payload.word,
            payload.is_correct,
            payload.vocabulary_id,
        )
    except Exception as error:
        raise_http_error(error)


@router.post("/drill/session/{session_id}/complete")
def complete_decode_session(session_id: int, payload: SessionComplete):
    try:
        return character_service.complete_session(
            session_id,
            payload.total_items,
            payload.correct_items,
            payload.incorrect_items,
        )
    except Exception as error:
        raise_http_error(error)


# Declared last: a bare ``/{hanzi}`` would otherwise swallow ``/stats`` and
# ``/modes``, since FastAPI matches routes in declaration order.
@router.get("/{hanzi}")
def get_character(hanzi: str):
    try:
        return character_service.get_character(hanzi)
    except Exception as error:
        raise_http_error(error)


@router.post("/{hanzi}/status")
def set_character_status(hanzi: str, payload: CharacterStatusUpdate):
    try:
        return character_service.set_status(hanzi, payload.status)
    except Exception as error:
        raise_http_error(error)
