"""Backup export / restore endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.routes.utils import raise_http_error
from backend.services import backup_service


router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/export")
def export_backup():
    payload = backup_service.export_data()
    filename = f"chinese-study-backup-{payload['exported_at'][:10]}.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_backup(request: Request):
    payload = await request.json()
    try:
        return backup_service.import_data(payload)
    except Exception as error:
        raise_http_error(error)
