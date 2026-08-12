from fastapi import APIRouter, Query

from backend.schemas import HskLevel, ProgressStatus
from backend.services import vocabulary_service
from backend.routes.utils import raise_http_error


router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])


@router.get("")
def get_vocabulary_list(
    search: str | None = Query(default=None, max_length=100),
    topic: str | None = Query(default=None, max_length=80),
    status: ProgressStatus | None = None,
    hsk_level: HskLevel | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    favorites_only: bool = False,
    sort: str = Query(default="id", pattern="^(id|hanzi|pinyin|level|frequency|recent|due)$"),
):
    return vocabulary_service.list_vocabulary(
        search=search,
        topic=topic,
        status=status.value if status else None,
        hsk_level=hsk_level.value if hsk_level else None,
        limit=limit,
        offset=offset,
        favorites_only=favorites_only,
        sort=sort,
    )


@router.get("/topics")
def get_topics():
    return {"items": vocabulary_service.list_topics()}


@router.get("/levels")
def get_levels():
    return {"items": vocabulary_service.list_hsk_levels()}


@router.get("/random")
def get_random_vocabulary(
    count: int = Query(default=10, ge=1, le=30),
    status: ProgressStatus | None = None,
    hsk_level: HskLevel | None = None,
):
    return {
        "items": vocabulary_service.get_random_vocabulary(
            count=count,
            status=status.value if status else None,
            hsk_level=hsk_level.value if hsk_level else None,
        )
    }


@router.get("/{vocabulary_id}")
def get_vocabulary_detail(vocabulary_id: int):
    try:
        return vocabulary_service.get_vocabulary(vocabulary_id)
    except Exception as error:
        raise_http_error(error)

