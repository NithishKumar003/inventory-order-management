from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

from app.database import Base, get_db
from app.main import app
from app.auth import get_current_user


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

test_user = {
    "id": 800001,
    "email": "coupon-test@example.com",
    "role": "admin",
    "is_active": True,
}


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return dict(test_user)


@pytest.fixture(autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)

    test_user["role"] = "admin"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    yield

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def valid_coupon_data():
    return {
        "code": "SAVE10",
        "discount_type": "PERCENT",
        "discount_value": 10,
        "minimum_order_amount": 100,
        "maximum_discount_amount": 500,
        "usage_limit": 100,
    }


def test_admin_can_create_coupon():
    response = client.post(
        "/coupons",
        json=valid_coupon_data(),
    )

    assert response.status_code == 201
    assert response.json()["code"] == "SAVE10"
    assert response.json()["discount_type"] == "PERCENT"
    assert response.json()["is_active"] is True


def test_customer_cannot_create_coupon():
    test_user["role"] = "customer"

    response = client.post(
        "/coupons",
        json=valid_coupon_data(),
    )

    assert response.status_code == 403


def test_duplicate_coupon_code_is_rejected():
    client.post("/coupons", json=valid_coupon_data())

    response = client.post(
        "/coupons",
        json=valid_coupon_data(),
    )

    assert response.status_code == 409


def test_percentage_discount_cannot_exceed_100():
    data = valid_coupon_data()
    data["discount_value"] = 110

    response = client.post("/coupons", json=data)

    assert response.status_code == 400


def test_invalid_coupon_date_range_is_rejected():
    data = valid_coupon_data()
    data["starts_at"] = "2026-12-01T00:00:00"
    data["expires_at"] = "2026-11-01T00:00:00"

    response = client.post("/coupons", json=data)

    assert response.status_code == 400


def test_admin_can_list_coupons():
    client.post("/coupons", json=valid_coupon_data())

    response = client.get("/coupons")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["code"] == "SAVE10"


def test_customer_cannot_list_coupons():
    test_user["role"] = "customer"

    response = client.get("/coupons")

    assert response.status_code == 403


def test_admin_can_deactivate_coupon():
    create_response = client.post(
        "/coupons",
        json=valid_coupon_data(),
    )
    coupon_id = create_response.json()["id"]

    response = client.patch(
        f"/coupons/{coupon_id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_can_reactivate_coupon():
    create_response = client.post(
        "/coupons",
        json=valid_coupon_data(),
    )
    coupon_id = create_response.json()["id"]

    client.patch(
        f"/coupons/{coupon_id}/status",
        json={"is_active": False},
    )

    response = client.patch(
        f"/coupons/{coupon_id}/status",
        json={"is_active": True},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_customer_cannot_change_coupon_status():
    create_response = client.post(
        "/coupons",
        json=valid_coupon_data(),
    )
    coupon_id = create_response.json()["id"]

    test_user["role"] = "customer"

    response = client.patch(
        f"/coupons/{coupon_id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 403


def test_update_nonexistent_coupon_returns_404():
    response = client.patch(
        "/coupons/999999/status",
        json={"is_active": False},
    )

    assert response.status_code == 404