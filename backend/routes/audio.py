from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from backend.routes.utils import raise_http_error
from backend.services import audio_service


router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.get("")
def get_audio(
    text: str = Query(min_length=1, max_length=200),
    voice: str = Query(default="female", pattern="^(female|male)$"),
):
    try:
        path = audio_service.get_or_create_audio(text, voice)
    except Exception as error:
        raise_http_error(error)
    return FileResponse(path, media_type="audio/mpeg")
