
import pytest
import httpx

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as return_main
from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    current_user = {
        "id": 7,
        "role": "customer",
        "_access_token": "test-token",
    }

    app.dependency_overrides[get_db] = override_get_db
    
        # Prevent real notification requests during tests.
    def mock_notification_post(*args, **kwargs):
        request = httpx.Request("POST", "http://test/notifications")
        return httpx.Response(201, request=request, json={"id": 1})

    def mock_notification_get(*args, **kwargs):
        request = httpx.Request("GET", "http://test/admin-ids")
        return httpx.Response(
            200,
            request=request,
            json={"admin_ids": []},
        )

    return_main.send_notification = lambda *args, **kwargs: None
    return_main.notify_admins = lambda *args, **kwargs: None
    
    app.dependency_overrides[get_current_user] = lambda: current_user

    with TestClient(app) as test_client:
        yield test_client, current_user, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class MockOrderResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://test/orders/1")
            response = httpx.Response(
                self.status_code,
                request=request,
            )
            raise httpx.HTTPStatusError(
                "Mock order error",
                request=request,
                response=response,
            )


def mock_delivered_order():
    return {
        "id": 1,
        "user_id": 7,
        "status": "Delivered",
        "items": [
            {
                "id": 10,
                "product_id": 25,
                "product_name": "Wireless Mouse",
                "quantity": 3,
                "unit_price": 599.00,
                "line_subtotal": 1797.00,
                "status": "Delivered",
                "cancelled_quantity": 0,
            }
        ],
    }


def mock_order_service(monkeypatch, order=None):
    order_data = order or mock_delivered_order()

    def fake_get(url, headers=None, timeout=None):
        assert headers == {
            "Authorization": "Bearer test-token"
        }
        return MockOrderResponse(order_data)

    monkeypatch.setattr(return_main.httpx, "get", fake_get)


def return_payload(**overrides):
    payload = {
        "order_id": 1,
        "order_item_id": 10,
        "quantity": 1,
        "reason": "Product is damaged",
        "idempotency_key": "return-test-001",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------
# Basic and customer return tests
# ---------------------------------------------------------

def test_health_endpoint(client):
    test_client, _, _ = client

    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_customer_can_create_return_request(client, monkeypatch):
    test_client, _, _ = client
    mock_order_service(monkeypatch)

    response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    assert response.status_code == 201, response.text

    result = response.json()

    assert result["user_id"] == 7
    assert result["order_id"] == 1
    assert result["order_item_id"] == 10
    assert result["product_id"] == 25
    assert result["quantity"] == 1
    assert result["status"] == "PENDING"


def test_return_request_is_idempotent(client, monkeypatch):
    test_client, _, _ = client
    mock_order_service(monkeypatch)

    first_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    second_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] == second_response.json()["id"]


def test_same_idempotency_key_with_different_data_is_rejected(
    client, monkeypatch
):
    test_client, _, _ = client
    mock_order_service(monkeypatch)

    first_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    second_response = test_client.post(
        "/returns",
        json=return_payload(quantity=2),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_return_rejects_order_that_is_not_delivered(
    client, monkeypatch
):
    test_client, _, _ = client

    order = mock_delivered_order()
    order["status"] = "Shipped"
    mock_order_service(monkeypatch, order)

    response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    assert response.status_code == 409


def test_return_rejects_order_owned_by_another_user(
    client, monkeypatch
):
    test_client, _, _ = client

    order = mock_delivered_order()
    order["user_id"] = 99
    mock_order_service(monkeypatch, order)

    response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    assert response.status_code == 404


def test_return_rejects_quantity_above_purchased_quantity(
    client, monkeypatch
):
    test_client, _, _ = client
    mock_order_service(monkeypatch)

    response = test_client.post(
        "/returns",
        json=return_payload(quantity=4),
    )

    assert response.status_code == 409


def test_return_rejects_already_cancelled_quantity(
    client, monkeypatch
):
    test_client, _, _ = client

    order = mock_delivered_order()
    order["items"][0]["cancelled_quantity"] = 2
    mock_order_service(monkeypatch, order)

    response = test_client.post(
        "/returns",
        json=return_payload(quantity=2),
    )

    assert response.status_code == 409


def test_return_rejects_item_not_in_order(client, monkeypatch):
    test_client, _, _ = client
    mock_order_service(monkeypatch)

    response = test_client.post(
        "/returns",
        json=return_payload(order_item_id=999),
    )

    assert response.status_code == 404


def test_customer_can_view_own_returns(client, monkeypatch):
    test_client, _, _ = client
    mock_order_service(monkeypatch)

    create_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    assert create_response.status_code == 201

    response = test_client.get("/returns/me")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["user_id"] == 7


def test_customer_cannot_view_admin_returns(client):
    test_client, _, _ = client

    response = test_client.get("/returns/admin")

    assert response.status_code == 403


# ---------------------------------------------------------
# Admin moderation tests
# ---------------------------------------------------------

def test_admin_can_view_all_returns(client):
    test_client, current_user, _ = client
    current_user["role"] = "admin"

    response = test_client.get("/returns/admin")

    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_approve_return(client, monkeypatch):
    test_client, current_user, _ = client
    current_user["role"] = "admin"
    mock_order_service(monkeypatch)

    create_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    return_id = create_response.json()["id"]

    response = test_client.patch(
        f"/returns/admin/{return_id}/moderation",
        json={
            "status": "APPROVED",
            "admin_note": "Return approved.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert response.json()["admin_note"] == "Return approved."


def test_admin_can_reject_return(client, monkeypatch):
    test_client, current_user, _ = client
    current_user["role"] = "admin"
    mock_order_service(monkeypatch)

    create_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    return_id = create_response.json()["id"]

    response = test_client.patch(
        f"/returns/admin/{return_id}/moderation",
        json={
            "status": "REJECTED",
            "admin_note": "Return is outside the return window.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_customer_cannot_moderate_return(client):
    test_client, _, _ = client

    response = test_client.patch(
        "/returns/admin/1/moderation",
        json={"status": "APPROVED"},
    )

    assert response.status_code == 403


def test_missing_return_cannot_be_moderated(client):
    test_client, current_user, _ = client
    current_user["role"] = "admin"

    response = test_client.patch(
        "/returns/admin/999/moderation",
        json={"status": "APPROVED"},
    )

    assert response.status_code == 404


def test_already_reviewed_return_cannot_be_moderated_again(
    client, monkeypatch
):
    test_client, current_user, _ = client
    current_user["role"] = "admin"
    mock_order_service(monkeypatch)

    create_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    return_id = create_response.json()["id"]

    first_response = test_client.patch(
        f"/returns/admin/{return_id}/moderation",
        json={"status": "APPROVED"},
    )

    second_response = test_client.patch(
        f"/returns/admin/{return_id}/moderation",
        json={"status": "REJECTED"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


# ---------------------------------------------------------
# Shared helpers for refund tests
# ---------------------------------------------------------

def create_approved_return(test_client, monkeypatch):
    mock_order_service(monkeypatch)

    create_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    assert create_response.status_code == 201, create_response.text

    return_id = create_response.json()["id"]

    # Get the actual user dictionary used by the test dependency.
    current_user = test_client.app.dependency_overrides[
        get_current_user
    ]()

    original_role = current_user["role"]

    try:
        current_user["role"] = "admin"

        moderation_response = test_client.patch(
            f"/returns/admin/{return_id}/moderation",
            json={
                "status": "APPROVED",
                "admin_note": "Approved for refund.",
            },
        )

        assert moderation_response.status_code == 200, (
            moderation_response.text
        )

    finally:
        current_user["role"] = original_role

    return return_id


def mock_payment_refund(monkeypatch, status="SUCCEEDED"):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        })

        request = httpx.Request("POST", url)

        return httpx.Response(
            201,
            request=request,
            json={
                "id": 501,
                "payment_id": 101,
                "user_id": 7,
                "amount": json["amount"],
                "reason": json["reason"],
                "idempotency_key": json["idempotency_key"],
                "status": status,
                "provider_reference": "TEST-REFUND-501",
                "failure_reason": (
                    "Test refund failure"
                    if status == "FAILED"
                    else None
                ),
                "created_at": "2026-10-30T10:00:00",
            },
        )

    monkeypatch.setattr(return_main.httpx, "post", fake_post)

    return calls


# ---------------------------------------------------------
# Return completion and payment refund tests
# ---------------------------------------------------------

def test_admin_can_complete_approved_return(client, monkeypatch):
    test_client, current_user, _ = client
    current_user["role"] = "admin"

    return_id = create_approved_return(test_client, monkeypatch)
    calls = mock_payment_refund(monkeypatch)

    response = test_client.post(
        f"/returns/admin/{return_id}/complete"
    )

    assert response.status_code == 200, response.text

    result = response.json()

    assert result["status"] == "COMPLETED"
    assert result["refund_status"] == "SUCCEEDED"
    assert result["payment_refund_id"] == 501
    assert float(result["refund_amount"]) == 599.0

    assert len(calls) == 1
    assert calls[0]["json"]["order_id"] == 1
    assert calls[0]["json"]["user_id"] == 7
    assert calls[0]["json"]["amount"] == "599.00"
    assert calls[0]["json"]["idempotency_key"] == f"return-{return_id}"


def test_customer_cannot_complete_return(client, monkeypatch):
    test_client, _, _ = client

    return_id = create_approved_return(test_client, monkeypatch)
    mock_payment_refund(monkeypatch)

    response = test_client.post(
        f"/returns/admin/{return_id}/complete"
    )

    assert response.status_code == 403


def test_missing_return_cannot_be_completed(client):
    test_client, current_user, _ = client
    current_user["role"] = "admin"

    response = test_client.post(
        "/returns/admin/999/complete"
    )

    assert response.status_code == 404


def test_pending_return_cannot_be_completed(client, monkeypatch):
    test_client, current_user, _ = client
    current_user["role"] = "admin"
    mock_order_service(monkeypatch)

    create_response = test_client.post(
        "/returns",
        json=return_payload(),
    )

    assert create_response.status_code == 201, create_response.text

    return_id = create_response.json()["id"]

    response = test_client.post(
        f"/returns/admin/{return_id}/complete"
    )

    assert response.status_code == 409


def test_pending_payment_refund_keeps_return_approved(
    client, monkeypatch
):
    test_client, current_user, _ = client
    current_user["role"] = "admin"

    return_id = create_approved_return(test_client, monkeypatch)
    mock_payment_refund(monkeypatch, status="PENDING")

    response = test_client.post(
        f"/returns/admin/{return_id}/complete"
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "APPROVED"
    assert response.json()["refund_status"] == "PENDING"
    assert response.json()["payment_refund_id"] == 501


def test_failed_payment_refund_keeps_return_approved(
    client, monkeypatch
):
    test_client, current_user, _ = client
    current_user["role"] = "admin"

    return_id = create_approved_return(test_client, monkeypatch)
    mock_payment_refund(monkeypatch, status="FAILED")

    response = test_client.post(
        f"/returns/admin/{return_id}/complete"
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "APPROVED"
    assert response.json()["refund_status"] == "FAILED"
    assert response.json()["refund_failure_reason"] == "Test refund failure"


def test_successful_refund_is_not_submitted_again(
    client, monkeypatch
):
    test_client, current_user, _ = client
    current_user["role"] = "admin"

    return_id = create_approved_return(test_client, monkeypatch)
    calls = mock_payment_refund(monkeypatch)

    first_response = test_client.post(
        f"/returns/admin/{return_id}/complete"
    )

    second_response = test_client.post(
        f"/returns/admin/{return_id}/complete"
    )

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text
    assert second_response.json()["status"] == "COMPLETED"
    assert len(calls) == 1
