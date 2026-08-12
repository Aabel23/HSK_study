import json

from fastapi import HTTPException

from backend.services.errors import InvalidOperationError, ResourceNotFoundError


def raise_http_error(error: Exception) -> None:
    if isinstance(error, HTTPException):
        raise error
    if isinstance(error, ResourceNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, InvalidOperationError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, (json.JSONDecodeError, UnicodeDecodeError, ValueError)):
        raise HTTPException(status_code=400, detail="Dữ liệu gửi lên không hợp lệ.") from error
    raise error
