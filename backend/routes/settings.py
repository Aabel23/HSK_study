"""User preference endpoints."""

from fastapi import APIRouter, Request

from backend.routes.utils import raise_http_error
from backend.services import settings_service
from backend.services.errors import InvalidOperationError


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return {"settings": settings_service.get_settings(), "defaults": settings_service.DEFAULT_SETTINGS}


@router.patch("")
async def update_settings(request: Request):
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise InvalidOperationError("Dữ liệu cài đặt không hợp lệ.")
        return {"settings": settings_service.update_settings(payload)}
    except Exception as error:
        raise_http_error(error)


@router.post("/reset")
def reset_settings():
    return {"settings": settings_service.reset_settings()}
