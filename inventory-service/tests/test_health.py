import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db
from app.models import Inventory, StockMovement


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


@pytest.fixture(autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "inventory-service",
    }


@patch("app.main.httpx.get")
def test_create_inventory(mock_get):
    mock_product_response = Mock()
    mock_product_response.status_code = 200
    mock_get.return_value = mock_product_response

    unique_product_id = int(uuid.uuid4().int % 1_000_000_000) + 1

    response = client.post(
        "/inventory",
        json={
            "product_id": unique_product_id,
            "quantity": 50,
        },
    )

    assert response.status_code == 201
    assert response.json()["product_id"] == unique_product_id
    assert response.json()["quantity"] == 50
    mock_get.assert_called_once()

@patch("app.main.httpx.get")
def test_duplicate_inventory(mock_get):
    mock_product_response = Mock()
    mock_product_response.status_code = 200
    mock_get.return_value = mock_product_response

    product_id = 123456789

    first_response = client.post(
        "/inventory",
        json={
            "product_id": product_id,
            "quantity": 50,
        },
    )

    second_response = client.post(
        "/inventory",
        json={
            "product_id": product_id,
            "quantity": 30,
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Inventory already exists for this product."
    )

@patch("app.main.httpx.get")
def test_increase_stock(mock_get):
    mock_get.return_value = Mock(status_code=200)
    product_id = 123456788

    # Create inventory first
    create_response = client.post(
        "/inventory",
        json={
            "product_id": product_id,
            "quantity": 10,
        },
    )

    assert create_response.status_code == 201

    # Add 5 units of stock
    movement_response = client.post(
        "/inventory/movements",
        json={
            "product_id": product_id,
            "quantity_change": 5,
            "reason": "New stock received",
        },
    )

    assert movement_response.status_code == 201
    assert movement_response.json()["quantity_change"] == 5

    # Verify the updated stock quantity
    inventory_response = client.get(
        f"/inventory/{product_id}"
    )

    assert inventory_response.status_code == 200
    assert inventory_response.json()["quantity"] == 15

def test_prevent_negative_stock():
    product_id = 123456787

    # Create inventory with 10 units
    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=product_id,
                quantity=10,
            )
        )
        db.commit()

    # Try to remove 15 units
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": product_id,
            "quantity_change": -15,
            "reason": "Damaged items removed",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Stock quantity cannot become negative."
    )

    # Verify the stock remains unchanged
    inventory_response = client.get(
        f"/inventory/{product_id}"
    )

    assert inventory_response.status_code == 200
    assert inventory_response.json()["quantity"] == 10

def test_stock_movement_history():
    product_id = 123456786

    # Create inventory directly in the test database
    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=product_id,
                quantity=10,
            )
        )
        db.commit()

    # Record a stock movement
    movement_response = client.post(
        "/inventory/movements",
        json={
            "product_id": product_id,
            "quantity_change": 5,
            "reason": "Restock received",
        },
    )

    assert movement_response.status_code == 201

    # Retrieve movement history for this product
    history_response = client.get(
        f"/inventory/movements?product_id={product_id}"
    )

    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert history_response.json()[0]["product_id"] == product_id
    assert history_response.json()[0]["quantity_change"] == 5
    assert history_response.json()[0]["reason"] == "Restock received"

def test_low_stock_endpoint():
    with TestSessionLocal() as db:
        db.add_all([
            Inventory(product_id=123456781, quantity=3),
            Inventory(product_id=123456780, quantity=20),
        ])
        db.commit()

    response = client.get("/inventory/low-stock?threshold=5")

    assert response.status_code == 200

    results = response.json()

    assert len(results) == 1
    assert results[0]["product_id"] == 123456781
    assert results[0]["quantity"] == 3

def test_get_inventory_by_product_id():
    product_id = 123456779

    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=product_id,
                quantity=25,
            )
        )
        db.commit()

    response = client.get(f"/inventory/{product_id}")

    assert response.status_code == 200
    assert response.json()["product_id"] == product_id
    assert response.json()["quantity"] == 25

def test_update_inventory_quantity():
    product_id = 123456778

    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=product_id,
                quantity=10,
            )
        )
        db.commit()

    response = client.put(
        f"/inventory/{product_id}",
        json={"quantity": 40},
    )

    assert response.status_code == 200
    assert response.json()["product_id"] == product_id
    assert response.json()["quantity"] == 40

def test_delete_inventory():
    product_id = 123456777

    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=product_id,
                quantity=15,
            )
        )
        db.commit()

    response = client.delete(
        f"/inventory/{product_id}"
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Inventory deleted successfully."
    )
    assert response.json()["product_id"] == product_id

    # Confirm the inventory no longer exists
    get_response = client.get(
        f"/inventory/{product_id}"
    )

    assert get_response.status_code == 404

def test_delete_nonexistent_inventory():
    product_id = 987654321

    response = client.delete(
        f"/inventory/{product_id}"
    )

    assert response.status_code == 404

def test_stock_movement_for_missing_inventory():
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": 987654320,
            "quantity_change": 5,
            "reason": "Restock received",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Inventory not found for this product."
    )

def test_stock_movement_rejects_zero_quantity_change():
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": 123456776,
            "quantity_change": 0,
            "reason": "Invalid stock change",
        },
    )

    assert response.status_code == 422

def test_stock_movement_rejects_short_reason():
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": 123456775,
            "quantity_change": 5,
            "reason": "OK",
        },
    )

    assert response.status_code == 422

def test_stock_movement_rejects_negative_product_id():
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": -1,
            "quantity_change": 5,
            "reason": "Restock received",
        },
    )

    assert response.status_code == 422

def test_stock_movement_rejects_missing_reason():
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": 123456774,
            "quantity_change": 5,
        },
    )

    assert response.status_code == 422

def test_stock_movement_rejects_missing_quantity_change():
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": 123456773,
            "reason": "Restock received",
        },
    )

    assert response.status_code == 422

def test_stock_movement_rejects_empty_reason():
    response = client.post(
        "/inventory/movements",
        json={
            "product_id": 123456772,
            "quantity_change": 5,
            "reason": "",
        },
    )

    assert response.status_code == 422

def test_create_inventory_rejects_negative_quantity():
    response = client.post(
        "/inventory",
        json={
            "product_id": 123456771,
            "quantity": -5,
        },
    )

    assert response.status_code == 422

@patch("app.main.httpx.get")
def test_create_inventory_rejects_nonexistent_product(mock_get):
    mock_get.return_value = Mock(status_code=404)

    response = client.post(
        "/inventory",
        json={
            "product_id": 987654321,
            "quantity": 10,
        },
    )

    assert response.status_code == 404

def test_update_inventory_rejects_negative_quantity():
    product_id = 123456770

    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=product_id,
                quantity=10,
            )
        )
        db.commit()

    response = client.put(
        f"/inventory/{product_id}",
        json={"quantity": -5},
    )

    assert response.status_code == 422

    # Confirm the original stock remains unchanged
    get_response = client.get(
        f"/inventory/{product_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["quantity"] == 10

def test_update_nonexistent_inventory():
    product_id = 987654322

    response = client.put(
        f"/inventory/{product_id}",
        json={"quantity": 20},
    )

    assert response.status_code == 404

def test_get_nonexistent_inventory():
    product_id = 987654323

    response = client.get(
        f"/inventory/{product_id}"
    )

    assert response.status_code == 404

def test_low_stock_uses_default_threshold():
    with TestSessionLocal() as db:
        db.add_all([
            Inventory(
                product_id=123456769,
                quantity=5,
            ),
            Inventory(
                product_id=123456768,
                quantity=10,
            ),
            Inventory(
                product_id=123456767,
                quantity=15,
            ),
        ])
        db.commit()

    response = client.get("/inventory/low-stock")

    assert response.status_code == 200

    products = response.json()
    product_ids = {
        product["product_id"] for product in products
    }

    assert 123456769 in product_ids
    assert 123456768 in product_ids
    assert 123456767 not in product_ids

def test_stock_movement_history_pagination():
    product_id = 123456766

    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=product_id,
                quantity=20,
            )
        )
        db.commit()

    first_response = client.post(
        "/inventory/movements",
        json={
            "product_id": product_id,
            "quantity_change": 5,
            "reason": "First restock",
        },
    )

    second_response = client.post(
        "/inventory/movements",
        json={
            "product_id": product_id,
            "quantity_change": 3,
            "reason": "Second restock",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get(
        f"/inventory/movements?product_id={product_id}&skip=0&limit=1"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

@patch("app.main.httpx.get")
def test_create_inventory_when_product_service_unavailable(mock_get):
    import httpx

    mock_get.side_effect = httpx.ConnectError(
        "Connection failed"
    )

    response = client.post(
        "/inventory",
        json={
            "product_id": 123456765,
            "quantity": 10,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Product Service is unavailable."
    )

@patch("app.main.httpx.get")
def test_create_inventory_when_product_service_returns_server_error(mock_get):
    mock_get.return_value = Mock(status_code=500)

    response = client.post(
        "/inventory",
        json={
            "product_id": 123456764,
            "quantity": 10,
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Could not verify product with Product Service."
    )

@patch("app.main.httpx.get")
def test_create_inventory_when_product_service_times_out(mock_get):
    import httpx

    mock_get.side_effect = httpx.ReadTimeout(
        "Product Service timed out"
    )

    response = client.post(
        "/inventory",
        json={
            "product_id": 123456763,
            "quantity": 10,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Product Service is unavailable."
    )

@patch("app.main.httpx.get")
def test_create_inventory_when_product_does_not_exist(mock_get):
    mock_get.return_value = Mock(status_code=404)

    product_id = 987654324

    response = client.post(
        "/inventory",
        json={
            "product_id": product_id,
            "quantity": 10,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Product does not exists."
    )

    inventory_response = client.get(
        f"/inventory/{product_id}"
    )

    assert inventory_response.status_code == 404

@patch("app.main.httpx.get")
def test_create_inventory_after_product_verification(mock_get):
    mock_get.return_value = Mock(status_code=200)

    product_id = 123456762

    response = client.post(
        "/inventory",
        json={
            "product_id": product_id,
            "quantity": 25,
        },
    )

    assert response.status_code == 201
    assert response.json()["product_id"] == product_id
    assert response.json()["quantity"] == 25

    mock_get.assert_called_once()

@patch("app.main.httpx.get")
def test_inventory_creation_does_not_create_duplicates(mock_get):
    mock_get.return_value = Mock(status_code=200)

    product_id = 123456761

    first_response = client.post(
        "/inventory",
        json={
            "product_id": product_id,
            "quantity": 10,
        },
    )

    second_response = client.post(
        "/inventory",
        json={
            "product_id": product_id,
            "quantity": 20,
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    get_response = client.get(
        f"/inventory/{product_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["quantity"] == 10

@patch("app.main.httpx.get")
def test_create_inventory_when_product_service_returns_503(mock_get):
    mock_get.return_value = Mock(status_code=503)

    response = client.post(
        "/inventory",
        json={
            "product_id": 123456760,
            "quantity": 10,
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Could not verify product with Product Service."
    )

def test_stock_movement_history_rejects_negative_skip():
    response = client.get(
        "/inventory/movements?skip=-1"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Skip cannot be negative."
    )
