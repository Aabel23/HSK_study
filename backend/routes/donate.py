"""Donation endpoints backed by PayOS."""

from fastapi import APIRouter, Query, Request

from backend.routes.utils import raise_http_error
from backend.schemas import DonationCreate
from backend.services import donate_service

router = APIRouter(prefix="/api/donate", tags=["donate"])


@router.get("/config")
def get_donate_config():
    """Whether donations are available, and the amounts the page should offer."""
    return donate_service.get_config()


@router.get("/summary")
def get_donate_summary():
    return donate_service.get_summary()


@router.get("/recent")
def list_recent_donations(limit: int = Query(default=10, ge=1, le=50)):
    return {"items": donate_service.list_recent(limit)}


@router.post("/session", status_code=201)
def create_donation(payload: DonationCreate, request: Request):
    try:
        # The QR is scanned on a phone, so the return URL has to point at the
        # origin the browser is really on, not at the server's own bind address.
        base_url = str(request.base_url).rstrip("/")
        return donate_service.create_donation(
            payload.amount, payload.message, payload.donor_name, base_url
        )
    except Exception as error:
        raise_http_error(error)


@router.get("/status/{order_code}")
def get_donation_status(order_code: int):
    try:
        return donate_service.check_status(order_code)
    except Exception as error:
        raise_http_error(error)


@router.post("/cancel/{order_code}")
def cancel_donation(order_code: int):
    try:
        return donate_service.cancel_donation(order_code)
    except Exception as error:
        raise_http_error(error)


@router.post("/webhook")
async def receive_webhook(request: Request):
    """Called by PayOS when a transfer settles.

    Only reachable when the app is exposed publicly; the page polls as well, so
    a missed webhook never leaves a donation stuck as pending.
    """
    try:
        return donate_service.handle_webhook(await request.body())
    except Exception as error:
        raise_http_error(error)
