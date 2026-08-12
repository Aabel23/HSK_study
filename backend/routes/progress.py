from fastapi import APIRouter

from backend.routes.utils import raise_http_error
from backend.schemas import ProgressStatusUpdate
from backend.services import progress_service


router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("")
def get_progress():
    return progress_service.get_progress_summary()


@router.get("/{vocabulary_id}")
def get_vocabulary_progress(vocabulary_id: int):
    try:
        return progress_service.get_item_progress(vocabulary_id)
    except Exception as error:
        raise_http_error(error)


@router.post("/status")
def set_vocabulary_status(payload: ProgressStatusUpdate):
    try:
        return progress_service.update_status(payload.vocabulary_id, payload.status.value)
    except Exception as error:
        raise_http_error(error)

