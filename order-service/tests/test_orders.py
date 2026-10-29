from decimal import Decimal
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Allow tests to import the Order Service application.
SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

from app.database import Base, get_db
from app.main import app
from app.auth import get_current_user
from app import main as order_main
from app.models import Order, OrderItem


# Use an in-memory database for tests.
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return {
        "id": 700001,
        "email": "order-test@example.com",
        "role": "customer",
        "is_active": True,
    }


@pytest.fixture(autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    yield

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


@pytest.fixture
def mock_services(monkeypatch):
    """Mock product pricing and inventory reservation services."""

    products = {
        700101: {
            "id": 700101,
            "name": "Test Headphones",
            "price": 100.00,
            "is_active": True,
        },
        700102: {
            "id": 700102,
            "name": "Test Mouse",
            "price": 50.00,
            "is_active": True,
        },
    }

    reservations = []

    def fake_get_product(product_id):
        from fastapi import HTTPException

        product = products.get(product_id)
        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found.",
            )

        return product

    def fake_reserve_inventory(
        reservation_key,
        product_id,
        quantity,
    ):
        reservations.append(
            {
                "reservation_key": reservation_key,
                "product_id": product_id,
                "quantity": quantity,
            }
        )
        return {"status": "reserved"}

    released_reservations = []

    def fake_release_inventory(reservation_key, reason):
        released_reservations.append(reservation_key)

    monkeypatch.setattr(
        order_main,
        "get_product",
        fake_get_product,
    )
    monkeypatch.setattr(
        order_main,
        "reserve_inventory",
        fake_reserve_inventory,
    )
    monkeypatch.setattr(
        order_main,
        "release_inventory",
        fake_release_inventory,
    )

    return {
        "reservations": reservations,
        "released_reservations": released_reservations,
    }


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "order-service"


def test_create_order_successfully(mock_services):
    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": 700101, "quantity": 2},
            ],
            "idempotency_key": "test-order-key-001",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == 700001
    assert data["status"] == "Confirmed"
    assert data["subtotal"] == 200.00
    assert data["tax_amount"] == 36.00
    assert data["shipping_amount"] == 50.00
    assert data["total_amount"] == 286.00
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == 700101
    assert data["items"][0]["quantity"] == 2
    assert len(mock_services["reservations"]) == 1


def test_create_order_rejects_unknown_product(mock_services):
    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": 799999, "quantity": 1},
            ],
            "idempotency_key": "test-order-key-002",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert response.status_code == 404
    assert len(mock_services["reservations"]) == 0


def test_create_order_combines_duplicate_product_lines(
    mock_services,
):
    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": 700101, "quantity": 1},
                {"product_id": 700101, "quantity": 2},
            ],
            "idempotency_key": "test-order-key-003",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3
    assert data["subtotal"] == 300.00

    assert len(mock_services["reservations"]) == 1
    assert mock_services["reservations"][0]["quantity"] == 3


def test_create_order_rejects_empty_items():
    response = client.post(
        "/orders",
        json={
            "items": [],
            "idempotency_key": "test-order-key-004",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert response.status_code == 422

def test_idempotency_key_rejects_different_order_details(
    mock_services,
):
    first_response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": 700101, "quantity": 1},
            ],
            "idempotency_key": "same-order-key-005",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": 700102, "quantity": 1},
            ],
            "idempotency_key": "same-order-key-005",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert second_response.status_code == 409
    assert len(mock_services["reservations"]) == 1


def test_insufficient_stock_does_not_create_order(
    mock_services,
    monkeypatch,
):
    from fastapi import HTTPException

    def reject_reservation(
        reservation_key,
        product_id,
        quantity,
    ):
        raise HTTPException(
            status_code=409,
            detail="Insufficient stock.",
        )

    monkeypatch.setattr(
        order_main,
        "reserve_inventory",
        reject_reservation,
    )

    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": 700101, "quantity": 999},
            ],
            "idempotency_key": "insufficient-stock-key-006",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert response.status_code == 409

    db = next(override_get_db())
    try:
        assert db.query(Order).count() == 0
    finally:
        db.close()


def test_order_history_returns_customer_orders(mock_services):
    first_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 1}],
            "idempotency_key": "history-order-key-007",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    second_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700102, "quantity": 2}],
            "idempotency_key": "history-order-key-008",
            "shipping_address": "20 Test Street, Test City",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get("/orders")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(
        order["user_id"] == 700001
        for order in response.json()
    )


def test_order_details_returns_existing_customer_order(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 1}],
            "idempotency_key": "details-order-key-009",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order_id = create_response.json()["id"]

    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 200
    assert response.json()["id"] == order_id
    assert response.json()["user_id"] == 700001


def test_order_details_hides_another_customers_order(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 1}],
            "idempotency_key": "private-order-key-010",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order_id = create_response.json()["id"]

    def another_customer():
        return {
            "id": 700002,
            "email": "another-customer@example.com",
            "role": "customer",
            "is_active": True,
        }

    app.dependency_overrides[get_current_user] = another_customer

    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 404


def test_partial_order_item_cancellation(mock_services, monkeypatch):
    partial_releases = []

    def fake_partially_release_inventory(
        reservation_key,
        cancellation_key,
        quantity,
        reason,
    ):
        partial_releases.append(
            {
                "reservation_key": reservation_key,
                "cancellation_key": cancellation_key,
                "quantity": quantity,
                "reason": reason,
            }
        )
        return {"status": "reserved"}

    monkeypatch.setattr(
        order_main,
        "partially_release_inventory",
        fake_partially_release_inventory,
    )

    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 3}],
            "idempotency_key": "cancel-order-key-011",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    created_order = create_response.json()
    order_id = created_order["id"]
    item_id = created_order["items"][0]["id"]

    response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-item-key-011",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "Confirmed"
    assert data["items"][0]["quantity"] == 3
    assert data["items"][0]["cancelled_quantity"] == 1
    assert data["items"][0]["status"] == "Confirmed"
    assert data["items"][0]["cancellation_reason"] == "Customer changed mind"

    assert len(partial_releases) == 1
    assert partial_releases[0]["reservation_key"] == (
        f"{created_order['order_number']}-700101"
    )
    assert partial_releases[0]["quantity"] == 1
    assert partial_releases[0]["cancellation_key"] == "cancel-item-key-011"


def test_partial_cancellation_retry_does_not_duplicate(
    mock_services, monkeypatch
):
    partial_releases = []

    def fake_partially_release_inventory(
        reservation_key,
        cancellation_key,
        quantity,
        reason,
    ):
        partial_releases.append(cancellation_key)
        return {"status": "reserved"}

    monkeypatch.setattr(
        order_main,
        "partially_release_inventory",
        fake_partially_release_inventory,
    )

    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 3}],
            "idempotency_key": "cancel-retry-order-012",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    cancellation_request = {
        "cancellation_key": "cancel-retry-key-012",
        "quantity": 1,
        "reason": "Customer changed mind",
    }

    first_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json=cancellation_request,
    )

    second_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json=cancellation_request,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    data = second_response.json()
    assert data["items"][0]["cancelled_quantity"] == 1
    assert len(partial_releases) == 1


def test_partial_cancellation_exceeding_remaining_quantity(
    mock_services, monkeypatch
):
    def fake_partially_release_inventory(
        reservation_key,
        cancellation_key,
        quantity,
        reason,
    ):
        return {"status": "reserved"}

    monkeypatch.setattr(
        order_main,
        "partially_release_inventory",
        fake_partially_release_inventory,
    )

    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 3}],
            "idempotency_key": "cancel-limit-order-013",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    first_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-limit-key-013",
            "quantity": 2,
            "reason": "Customer changed mind",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["items"][0]["cancelled_quantity"] == 2

    second_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-limit-key-014",
            "quantity": 2,
            "reason": "Customer changed mind",
        },
    )

    assert second_response.status_code == 409
    assert "exceeds the remaining quantity" in (
        second_response.json()["detail"]
    )


def test_cancellation_key_reused_with_different_details(
    mock_services, monkeypatch
):
    partial_releases = []

    def fake_partially_release_inventory(
        reservation_key,
        cancellation_key,
        quantity,
        reason,
    ):
        partial_releases.append(cancellation_key)
        return {"status": "reserved"}

    monkeypatch.setattr(
        order_main,
        "partially_release_inventory",
        fake_partially_release_inventory,
    )

    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 3}],
            "idempotency_key": "cancel-key-order-014",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    first_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-reuse-key-014",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    second_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-reuse-key-014",
            "quantity": 2,
            "reason": "Customer changed mind",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert len(partial_releases) == 1
    assert second_response.json()["detail"] == (
        "Cancellation key was already used with different details."
    )

def test_partial_cancellation_order_not_found(monkeypatch):
    response = client.post(
        "/orders/999999/items/1/cancel",
        json={
            "cancellation_key": "cancel-missing-order-015",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found."

def test_partial_cancellation_item_not_found(
    mock_services, monkeypatch
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "cancel-item-order-016",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order_id = create_response.json()["id"]

    response = client.post(
        f"/orders/{order_id}/items/999999/cancel",
        json={
            "cancellation_key": "cancel-missing-item-016",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order item not found."

def test_cannot_cancel_item_after_order_shipped(
    mock_services, monkeypatch
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "cancel-shipped-order-017",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    # Mark the order as shipped in the test database.
    from app.models import Order

    db = TestSessionLocal()
    try:
        order_record = db.query(Order).filter(
            Order.id == order_id
        ).first()
        order_record.status = "Shipped"
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-shipped-key-017",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This order can no longer be cancelled."
    )

def test_cannot_cancel_item_after_order_delivered(
    mock_services, monkeypatch
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "cancel-delivered-order-018",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    db = TestSessionLocal()
    try:
        from app.models import Order

        order_record = (
            db.query(Order)
            .filter(Order.id == order_id)
            .first()
        )
        order_record.status = "Delivered"
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-delivered-key-018",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This order can no longer be cancelled."
    )

def test_cannot_cancel_already_cancelled_item(
    mock_services, monkeypatch
):
    def fake_partially_release_inventory(
        reservation_key,
        cancellation_key,
        quantity,
        reason,
    ):
        return {"status": "released"}

    monkeypatch.setattr(
        order_main,
        "partially_release_inventory",
        fake_partially_release_inventory,
    )

    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "cancel-already-order-019",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    first_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-all-key-019",
            "quantity": 2,
            "reason": "Customer changed mind",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["items"][0]["status"] == "Cancelled"

    second_response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-again-key-019",
            "quantity": 1,
            "reason": "Customer changed mind again",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "This order can no longer be cancelled."
    )

def test_cannot_cancel_another_users_order_item(
    mock_services, monkeypatch
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "cancel-owner-order-020",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    # Change the order owner in the test database.
    db = TestSessionLocal()
    try:
        order_record = (
            db.query(Order)
            .filter(Order.id == order_id)
            .first()
        )
        order_record.user_id = 700002
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/orders/{order_id}/items/{item_id}/cancel",
        json={
            "cancellation_key": "cancel-owner-key-020",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found."

def test_partial_cancellation_rejects_zero_quantity():
    response = client.post(
        "/orders/1/items/1/cancel",
        json={
            "cancellation_key": "cancel-zero-key-021",
            "quantity": 0,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 422


def test_partial_cancellation_rejects_short_reason():
    response = client.post(
        "/orders/1/items/1/cancel",
        json={
            "cancellation_key": "cancel-short-reason-022",
            "quantity": 1,
            "reason": "No",
        },
    )

    assert response.status_code == 422

def test_partial_cancellation_rejects_short_cancellation_key():
    response = client.post(
        "/orders/1/items/1/cancel",
        json={
            "cancellation_key": "short",
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 422

def test_partial_cancellation_rejects_long_cancellation_key():
    response = client.post(
        "/orders/1/items/1/cancel",
        json={
            "cancellation_key": "k" * 151,
            "quantity": 1,
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 422

def test_full_order_cancellation(mock_services):
    create_response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": 700101, "quantity": 2},
                {"product_id": 700102, "quantity": 1},
            ],
            "idempotency_key": "full-cancel-order-023",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()

    response = client.post(
        f"/orders/{order['id']}/cancel",
        json={
            "cancellation_key": "full-cancel-key-023",
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "Cancelled"

    for item in data["items"]:
        assert item["status"] == "Cancelled"
        assert item["cancelled_quantity"] == item["quantity"]

    expected_keys = {
        f"{order['order_number']}-700101",
        f"{order['order_number']}-700102",
    }
    assert set(mock_services["released_reservations"]) == expected_keys

def test_full_order_cancellation_retry_does_not_release_twice(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "full-cancel-retry-order-024",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()

    cancellation_request = {
        "cancellation_key": "full-cancel-retry-key-024",
        "reason": "Customer changed mind",
    }

    first_response = client.post(
        f"/orders/{order['id']}/cancel",
        json=cancellation_request,
    )

    second_response = client.post(
        f"/orders/{order['id']}/cancel",
        json=cancellation_request,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert second_response.json()["status"] == "Cancelled"
    assert mock_services["released_reservations"] == [
        f"{order['order_number']}-700101"
    ]

def test_full_order_cancellation_key_reused_with_different_reason(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "full-cancel-key-order-025",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()

    first_response = client.post(
        f"/orders/{order['id']}/cancel",
        json={
            "cancellation_key": "full-cancel-mismatch-025",
            "reason": "Customer changed mind",
        },
    )

    second_response = client.post(
        f"/orders/{order['id']}/cancel",
        json={
            "cancellation_key": "full-cancel-mismatch-025",
            "reason": "Ordered by mistake",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Cancellation key was already used with different details."
    )

    assert len(mock_services["released_reservations"]) == 1

def test_full_order_cancellation_order_not_found():
    response = client.post(
        "/orders/999999/cancel",
        json={
            "cancellation_key": "full-cancel-missing-026",
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found."

def test_full_order_cancellation_rejects_shipped_order(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "full-cancel-shipped-027",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()

    db = TestSessionLocal()
    try:
        order_record = (
            db.query(Order)
            .filter(Order.id == order["id"])
            .first()
        )
        order_record.status = "Shipped"
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/orders/{order['id']}/cancel",
        json={
            "cancellation_key": "full-cancel-shipped-key-027",
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This order can no longer be cancelled."
    )
    assert mock_services["released_reservations"] == []

def test_full_order_cancellation_rejects_delivered_order(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "full-cancel-delivered-028",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()

    db = TestSessionLocal()
    try:
        order_record = (
            db.query(Order)
            .filter(Order.id == order["id"])
            .first()
        )
        order_record.status = "Delivered"
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/orders/{order['id']}/cancel",
        json={
            "cancellation_key": "full-cancel-delivered-key-028",
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This order can no longer be cancelled."
    )
    assert mock_services["released_reservations"] == []

def test_full_order_cancellation_cannot_cancel_another_users_order(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "full-cancel-other-user-029",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()

    db = TestSessionLocal()
    try:
        order_record = (
            db.query(Order)
            .filter(Order.id == order["id"])
            .first()
        )

        # Simulate an order belonging to a different customer.
        order_record.user_id = 700002
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/orders/{order['id']}/cancel",
        json={
            "cancellation_key": "full-cancel-other-user-key-029",
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found."
    assert mock_services["released_reservations"] == []

def test_full_order_cancellation_rejects_invalid_input(
    mock_services,
):
    create_response = client.post(
        "/orders",
        json={
            "items": [{"product_id": 700101, "quantity": 2}],
            "idempotency_key": "full-cancel-invalid-030",
            "shipping_address": "10 Test Street, Test City",
        },
    )

    assert create_response.status_code == 201
    order = create_response.json()

    response = client.post(
        f"/orders/{order['id']}/cancel",
        json={
            "cancellation_key": "short",
            "reason": "Customer changed mind",
        },
    )

    assert response.status_code == 422
    assert mock_services["released_reservations"] == []
