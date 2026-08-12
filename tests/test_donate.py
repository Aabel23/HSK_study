"""Donation flow.

Nothing here talks to PayOS. The SDK is replaced with a stub, so the tests
exercise the parts this project owns -- validation, persistence, status
transitions and the disabled state -- without moving money or depending on a
network round trip.
"""

from __future__ import annotations

import pytest

from backend.services import donate_service
from backend.settings import reset_settings_cache


@pytest.fixture()
def payos_enabled(monkeypatch):
    monkeypatch.setenv("PAYOS_CLIENT_ID", "test-client")
    monkeypatch.setenv("PAYOS_API_KEY", "test-key")
    monkeypatch.setenv("PAYOS_CHECKSUM_KEY", "test-checksum")
    reset_settings_cache()
    yield
    reset_settings_cache()


class _StubPaymentRequests:
    def __init__(self, status: str = "PENDING"):
        self.status = status
        self.created: list[object] = []
        self.cancelled: list[int] = []

    def create(self, payment_data):
        self.created.append(payment_data)
        return type(
            "Response",
            (),
            {
                "checkout_url": f"https://pay.example/{payment_data.order_code}",
                "qr_code": "00020101021238540010A00000072701",
                "payment_link_id": "link-123",
            },
        )()

    def get(self, id):  # noqa: A002 - matches the SDK signature
        return type("Link", (), {"status": self.status})()

    def cancel(self, id, cancellation_reason=None):  # noqa: A002
        self.cancelled.append(id)
        return None


class _StubClient:
    def __init__(self, status: str = "PENDING"):
        self.payment_requests = _StubPaymentRequests(status)


@pytest.fixture()
def stub_payos(monkeypatch, payos_enabled):
    stub = _StubClient()
    monkeypatch.setattr(donate_service, "_client", lambda: stub)
    return stub


# --------------------------------------------------------------------------
# Disabled state
# --------------------------------------------------------------------------

def test_config_reports_disabled_without_credentials(client):
    data = client.get("/api/donate/config").json()
    assert data["enabled"] is False
    # The page still needs these to render its explanation.
    assert data["recipient"]
    assert data["min_amount"] > 0


def test_creating_a_donation_without_credentials_is_rejected(client):
    response = client.post("/api/donate/session", json={"amount": 50_000})
    assert response.status_code == 409
    assert "PayOS" in response.json()["detail"]


def test_summary_and_recent_work_without_credentials(client):
    """The history must not break just because the payment gateway is off."""
    assert client.get("/api/donate/summary").json() == {
        "paid_count": 0,
        "paid_total": 0,
        "last_paid_at": None,
    }
    assert client.get("/api/donate/recent").json() == {"items": []}


# --------------------------------------------------------------------------
# Enabled state
# --------------------------------------------------------------------------

def test_config_reports_enabled_with_credentials(client, payos_enabled):
    data = client.get("/api/donate/config").json()
    assert data["enabled"] is True
    assert data["suggested_amounts"]


def test_config_never_leaks_the_keys(client, payos_enabled):
    body = client.get("/api/donate/config").text
    assert "test-key" not in body
    assert "test-checksum" not in body
    assert "test-client" not in body


def test_create_donation_persists_a_pending_row(client, stub_payos):
    created = client.post(
        "/api/donate/session",
        json={"amount": 50_000, "message": "Cảm ơn", "donor_name": "Minh"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "pending"
    assert body["amount"] == 50_000
    assert body["message"] == "Cảm ơn"
    assert body["qr_code"]

    listed = client.get("/api/donate/recent").json()["items"]
    assert [item["order_code"] for item in listed] == [body["order_code"]]


@pytest.mark.parametrize("amount", [1_500, 20_000_000])
def test_amount_outside_the_configured_range_is_rejected(client, stub_payos, amount):
    response = client.post("/api/donate/session", json={"amount": amount})
    assert response.status_code == 409
    assert not stub_payos.payment_requests.created


def test_amount_outside_the_schema_range_is_rejected(client, stub_payos):
    assert client.post("/api/donate/session", json={"amount": 0}).status_code == 422


def test_paid_status_is_persisted_and_counted(client, stub_payos):
    order_code = client.post("/api/donate/session", json={"amount": 50_000}).json()["order_code"]

    stub_payos.payment_requests.status = "PAID"
    updated = client.get(f"/api/donate/status/{order_code}").json()
    assert updated["status"] == "paid"
    assert updated["paid_at"]

    summary = client.get("/api/donate/summary").json()
    assert summary == {
        "paid_count": 1,
        "paid_total": 50_000,
        "last_paid_at": updated["paid_at"],
    }


def test_a_settled_donation_is_not_re_queried(client, stub_payos):
    """Once paid, the local record is final -- a flaky network must not undo it."""
    order_code = client.post("/api/donate/session", json={"amount": 20_000}).json()["order_code"]
    stub_payos.payment_requests.status = "PAID"
    assert client.get(f"/api/donate/status/{order_code}").json()["status"] == "paid"

    # Even if PayOS started answering differently, the settled row stands.
    stub_payos.payment_requests.status = "CANCELLED"
    assert client.get(f"/api/donate/status/{order_code}").json()["status"] == "paid"


def test_cancel_marks_the_donation_cancelled(client, stub_payos):
    order_code = client.post("/api/donate/session", json={"amount": 20_000}).json()["order_code"]
    assert client.post(f"/api/donate/cancel/{order_code}").json()["status"] == "cancelled"
    assert stub_payos.payment_requests.cancelled == [order_code]

    # A cancelled donation counts for nothing.
    assert client.get("/api/donate/summary").json()["paid_total"] == 0


def test_cancelling_twice_is_rejected(client, stub_payos):
    order_code = client.post("/api/donate/session", json={"amount": 20_000}).json()["order_code"]
    client.post(f"/api/donate/cancel/{order_code}")
    assert client.post(f"/api/donate/cancel/{order_code}").status_code == 409


def test_unknown_order_code_is_a_404(client, stub_payos):
    assert client.get("/api/donate/status/424242").status_code == 404


def test_webhook_marks_a_donation_paid(client, stub_payos, monkeypatch):
    order_code = client.post("/api/donate/session", json={"amount": 30_000}).json()["order_code"]

    class _Webhooks:
        def verify(self, payload):
            return type("Data", (), {"order_code": order_code})()

    stub_payos.webhooks = _Webhooks()
    assert client.post("/api/donate/webhook", content=b"{}").json()["status"] == "paid"


def test_webhook_for_an_unknown_order_is_acknowledged(client, stub_payos):
    """PayOS retries on failure, so an order we never saw must not 500."""

    class _Webhooks:
        def verify(self, payload):
            return type("Data", (), {"order_code": 999_111})()

    stub_payos.webhooks = _Webhooks()
    body = client.post("/api/donate/webhook", content=b"{}").json()
    assert body == {"order_code": 999_111, "status": "unknown"}


def test_unverifiable_webhook_is_rejected(client, stub_payos):
    class _Webhooks:
        def verify(self, payload):
            raise ValueError("bad signature")

    stub_payos.webhooks = _Webhooks()
    assert client.post("/api/donate/webhook", content=b"{}").status_code == 409
