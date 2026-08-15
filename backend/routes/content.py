from fastapi import APIRouter

from backend.services import content_service


router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/overview")
def get_content_overview():
    """Size and freshness of every question pool, for the Ngân hàng đề screen."""
    return content_service.get_overview()
