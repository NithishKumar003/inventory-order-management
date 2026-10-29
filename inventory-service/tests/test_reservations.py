import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db
from app.models import Inventory


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

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_database():
    # Create the isolated test tables.
    Base.metadata.create_all(bind=test_engine)

    # Ensure these tests use the test database.
    app.dependency_overrides[get_db] = override_get_db

    # Add fresh test stock before each test.
    with TestSessionLocal() as db:
        db.add(
            Inventory(
                product_id=700001,
                quantity=10,
            )
        )
        db.commit()

    yield

    # Remove the override and clean up the test tables.
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)


def teardown_function():
    Base.metadata.drop_all(bind=test_engine)


def test_reserve_stock_successfully():
    response = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "test-reserve-001",
            "product_id": 700001,
            "quantity": 3,
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "reserved"
    assert response.json()["quantity"] == 3

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        assert inventory.quantity == 7


def test_duplicate_reservation_does_not_deduct_stock_twice():
    payload = {
        "reservation_key": "test-reserve-002",
        "product_id": 700001,
        "quantity": 3,
    }

    first_response = client.post(
        "/inventory/reservations",
        json=payload,
    )
    second_response = client.post(
        "/inventory/reservations",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        assert inventory.quantity == 7


def test_reservation_rejects_insufficient_stock():
    response = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "test-reserve-003",
            "product_id": 700001,
            "quantity": 11,
        },
    )

    assert response.status_code == 409

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        assert inventory.quantity == 10


def test_release_restores_stock_only_once():
    reservation = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "test-reserve-004",
            "product_id": 700001,
            "quantity": 4,
        },
    )

    assert reservation.status_code == 201

    release_url = (
        "/inventory/reservations/"
        "test-reserve-004/release"
    )
    release_payload = {
        "reason": "Test cancellation release",
    }

    first_release = client.post(
        release_url,
        json=release_payload,
    )
    second_release = client.post(
        release_url,
        json=release_payload,
    )

    assert first_release.status_code == 200
    assert first_release.json()["status"] == "released"
    assert second_release.status_code == 200

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        assert inventory.quantity == 10



def test_partial_release_restores_only_requested_quantity():
    reservation_response = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "partial-release-test-01",
            "product_id": 700001,
            "quantity": 5,
        },
    )

    assert reservation_response.status_code == 201

    response = client.post(
        "/inventory/reservations/partial-release-test-01/partial-release",
        json={
            "release_key": "partial-release-key-01",
            "quantity": 2,
            "reason": "Partial order cancellation",
        },
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 5
    assert response.json()["released_quantity"] == 2
    assert response.json()["status"] == "reserved"

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        assert inventory.quantity == 7


def test_partial_release_cannot_exceed_remaining_quantity():
    reservation_response = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "partial-release-test-02",
            "product_id": 700001,
            "quantity": 5,
        },
    )

    assert reservation_response.status_code == 201

    response = client.post(
        "/inventory/reservations/partial-release-test-02/partial-release",
        json={
            "release_key": "partial-release-key-02",
            "quantity": 6,
            "reason": "Invalid cancellation quantity",
        },
    )

    assert response.status_code == 409

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        assert inventory.quantity == 5


def test_repeating_partial_release_does_not_restore_stock_twice():
    reservation_response = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "idempotent-reservation-01",
            "product_id": 700001,
            "quantity": 5,
        },
    )
    assert reservation_response.status_code == 201

    release_payload = {
        "release_key": "idempotent-release-01",
        "quantity": 2,
        "reason": "Partial order cancellation",
    }

    first_response = client.post(
        "/inventory/reservations/idempotent-reservation-01/partial-release",
        json=release_payload,
    )
    assert first_response.status_code == 200
    assert first_response.json()["released_quantity"] == 2

    second_response = client.post(
        "/inventory/reservations/idempotent-reservation-01/partial-release",
        json=release_payload,
    )
    assert second_response.status_code == 200
    assert second_response.json()["released_quantity"] == 2

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        assert inventory.quantity == 7


def test_full_release_after_partial_release_restores_only_remaining_stock():
    reservation_response = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "partial-then-full-01",
            "product_id": 700001,
            "quantity": 5,
        },
    )
    assert reservation_response.status_code == 201

    partial_response = client.post(
        "/inventory/reservations/partial-then-full-01/partial-release",
        json={
            "release_key": "partial-then-full-release-01",
            "quantity": 2,
            "reason": "Partial order cancellation",
        },
    )
    assert partial_response.status_code == 200
    assert partial_response.json()["released_quantity"] == 2

    full_response = client.post(
        "/inventory/reservations/partial-then-full-01/release",
        json={"reason": "Order cancellation completed"},
    )
    assert full_response.status_code == 200
    assert full_response.json()["released_quantity"] == 5
    assert full_response.json()["status"] == "released"

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        # Starting stock 10; reserve 5; release 2; release remaining 3.
        assert inventory.quantity == 10


def test_partial_release_rejects_reused_key_with_different_details():
    reservation_response = client.post(
        "/inventory/reservations",
        json={
            "reservation_key": "release-key-conflict-01",
            "product_id": 700001,
            "quantity": 5,
        },
    )
    assert reservation_response.status_code == 201

    first_response = client.post(
        "/inventory/reservations/release-key-conflict-01/partial-release",
        json={
            "release_key": "release-key-conflict-test-01",
            "quantity": 2,
            "reason": "Partial order cancellation",
        },
    )
    assert first_response.status_code == 200

    conflicting_response = client.post(
        "/inventory/reservations/release-key-conflict-01/partial-release",
        json={
            "release_key": "release-key-conflict-test-01",
            "quantity": 3,
            "reason": "Partial order cancellation",
        },
    )
    assert conflicting_response.status_code == 409

    with TestSessionLocal() as db:
        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == 700001)
            .first()
        )
        # Only the first release of 2 units should have been applied.
        assert inventory.quantity == 7
