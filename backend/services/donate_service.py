"""Donations through PayOS.

The flow is the one PayOS documents for VietQR: create a payment link, show the
returned QR payload, then poll the link until the bank confirms. A webhook
endpoint exists too, but polling is what actually works here -- the app normally
runs on `127.0.0.1`, where PayOS cannot reach it.

Everything about this feature is optional. The keys authorise real transfers, so
they only ever come from the environment; with no keys configured the service
reports itself disabled and the rest of the app is unaffected. The `payos` SDK is
imported lazily for the same reason: a packaged build without it must still
start.
"""

from __future__ import annotations

import time
from typing import Any

from backend.database import get_connection, utc_now
from backend.services.errors import InvalidOperationError, ResourceNotFoundError
from backend.settings import get_settings

# PayOS order codes are positive int32 values.
_MAX_ORDER_CODE = 2_147_483_647

# PayOS truncates the transfer description; keep well inside the limit so the
# order code stays readable on the bank statement.
_MAX_DESCRIPTION = 25

_STATUS_MAP = {
    "PAID": "paid",
    "CANCELLED": "cancelled",
    "EXPIRED": "expired",
    "PENDING": "pending",
    "PROCESSING": "pending",
}


def _client():
    """Build a PayOS client, or explain why donations are unavailable."""
    settings = get_settings()
    if not settings.payos_configured:
        raise InvalidOperationError(
            "Chưa cấu hình PayOS. Đặt PAYOS_CLIENT_ID, PAYOS_API_KEY và "
            "PAYOS_CHECKSUM_KEY trong biến môi trường hoặc file .env."
        )
    try:
        from payos import PayOS
    except ImportError as error:  # pragma: no cover - depends on the install
        raise InvalidOperationError(
            "Thiếu thư viện payos. Cài bằng: pip install payos"
        ) from error
    return PayOS(
        client_id=settings.payos_client_id,
        api_key=settings.payos_api_key,
        checksum_key=settings.payos_checksum_key,
    )


def get_config() -> dict[str, Any]:
    """What the donate page needs to render, with no secrets in it."""
    settings = get_settings()
    return {
        "enabled": settings.payos_configured,
        "recipient": settings.donate_recipient,
        "min_amount": settings.donate_min_amount,
        "max_amount": settings.donate_max_amount,
        "suggested_amounts": [20_000, 50_000, 100_000, 200_000],
        "currency": "VND",
    }


def _row_to_donation(row: Any) -> dict[str, Any]:
    return {
        "order_code": row["order_code"],
        "amount": row["amount"],
        "message": row["message"],
        "donor_name": row["donor_name"],
        "status": row["status"],
        "checkout_url": row["checkout_url"],
        "qr_code": row["qr_code"],
        "created_at": row["created_at"],
        "paid_at": row["paid_at"],
    }


def _next_order_code(connection: Any) -> int:
    """A unique positive int32, retried in the astronomically rare collision."""
    for _ in range(10):
        candidate = int(time.time() * 1000) % _MAX_ORDER_CODE
        exists = connection.execute(
            "SELECT 1 FROM donations WHERE order_code = ?", (candidate,)
        ).fetchone()
        if not exists:
            return candidate
        time.sleep(0.002)
    raise InvalidOperationError("Không tạo được mã đơn, vui lòng thử lại.")


def create_donation(
    amount: int,
    message: str = "",
    donor_name: str = "",
    base_url: str = "",
) -> dict[str, Any]:
    """Create a PayOS payment link and remember it locally."""
    settings = get_settings()
    if not settings.donate_min_amount <= amount <= settings.donate_max_amount:
        raise InvalidOperationError(
            f"Số tiền phải từ {settings.donate_min_amount:,} đến "
            f"{settings.donate_max_amount:,} đồng."
        )

    client = _client()
    from payos.types import CreatePaymentLinkRequest

    now = utc_now()
    with get_connection() as connection:
        order_code = _next_order_code(connection)

    # The return/cancel URLs have to be reachable from the phone that scanned
    # the QR, so they follow whichever origin the browser is actually using.
    origin = (settings.donate_base_url or base_url or "").rstrip("/")
    origin = origin or f"http://{settings.host}:{settings.port}"

    try:
        response = client.payment_requests.create(
            payment_data=CreatePaymentLinkRequest(
                order_code=order_code,
                amount=amount,
                description=f"Donate {order_code}"[:_MAX_DESCRIPTION],
                cancel_url=f"{origin}/#/donate?status=cancel",
                return_url=f"{origin}/#/donate?status=success",
            )
        )
    except Exception as error:  # PayOS raises its own exception hierarchy
        raise InvalidOperationError(f"PayOS từ chối tạo đơn: {error}") from error

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO donations (
                order_code, amount, message, donor_name, status,
                checkout_url, qr_code, payment_link_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
            """,
            (
                order_code,
                amount,
                message.strip(),
                donor_name.strip(),
                response.checkout_url,
                response.qr_code,
                response.payment_link_id,
                now,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM donations WHERE order_code = ?", (order_code,)
        ).fetchone()
    return _row_to_donation(row)


def _store_status(order_code: int, status: str) -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM donations WHERE order_code = ?", (order_code,)
        ).fetchone()
        if not row:
            raise ResourceNotFoundError("Không tìm thấy lượt ủng hộ.")
        if row["status"] != status:
            connection.execute(
                """
                UPDATE donations
                SET status = ?,
                    updated_at = ?,
                    paid_at = CASE WHEN ? = 'paid' THEN COALESCE(paid_at, ?) ELSE paid_at END
                WHERE order_code = ?
                """,
                (status, now, status, now, order_code),
            )
        row = connection.execute(
            "SELECT * FROM donations WHERE order_code = ?", (order_code,)
        ).fetchone()
    return _row_to_donation(row)


def check_status(order_code: int) -> dict[str, Any]:
    """Ask PayOS where the transfer stands and persist the answer.

    A settled donation is never re-queried: the local record is already final,
    and asking again would only add latency and a chance of a network error
    turning a completed donation back into "unknown".
    """
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM donations WHERE order_code = ?", (order_code,)
        ).fetchone()
    if not row:
        raise ResourceNotFoundError("Không tìm thấy lượt ủng hộ.")
    if row["status"] != "pending":
        return _row_to_donation(row)

    client = _client()
    try:
        link = client.payment_requests.get(id=order_code)
    except Exception as error:
        raise InvalidOperationError(f"Không kiểm tra được trạng thái: {error}") from error

    return _store_status(order_code, _STATUS_MAP.get(str(link.status).upper(), "pending"))


def cancel_donation(order_code: int, reason: str = "Người dùng huỷ") -> dict[str, Any]:
    """Cancel a pending link so it stops occupying the donor's banking app."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT status FROM donations WHERE order_code = ?", (order_code,)
        ).fetchone()
    if not row:
        raise ResourceNotFoundError("Không tìm thấy lượt ủng hộ.")
    if row["status"] != "pending":
        raise InvalidOperationError("Lượt ủng hộ này đã kết thúc.")

    client = _client()
    try:
        client.payment_requests.cancel(id=order_code, cancellation_reason=reason)
    except Exception as error:
        raise InvalidOperationError(f"Không huỷ được đơn: {error}") from error
    return _store_status(order_code, "cancelled")


def handle_webhook(payload: bytes | str | dict) -> dict[str, Any]:
    """Mark a donation paid from a PayOS webhook, after verifying the signature."""
    client = _client()
    try:
        data = client.webhooks.verify(payload)
    except Exception as error:
        raise InvalidOperationError(f"Webhook không hợp lệ: {error}") from error

    order_code = getattr(data, "order_code", None)
    if order_code is None:
        raise InvalidOperationError("Webhook thiếu mã đơn.")
    try:
        return _store_status(int(order_code), "paid")
    except ResourceNotFoundError:
        # A webhook for an order this database has never seen is not an error
        # worth retrying -- acknowledge it so PayOS stops resending.
        return {"order_code": int(order_code), "status": "unknown"}


def list_recent(limit: int = 10) -> list[dict[str, Any]]:
    """Recent donations, newest first, for the history list on the page."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM donations ORDER BY created_at DESC, order_code DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_donation(row) for row in rows]


def get_summary() -> dict[str, Any]:
    """Totals shown above the donate form."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'paid') AS paid_count,
                COALESCE(SUM(amount) FILTER (WHERE status = 'paid'), 0) AS paid_total,
                MAX(paid_at) AS last_paid_at
            FROM donations
            """
        ).fetchone()
    return {
        "paid_count": row["paid_count"] or 0,
        "paid_total": row["paid_total"] or 0,
        "last_paid_at": row["last_paid_at"],
    }
