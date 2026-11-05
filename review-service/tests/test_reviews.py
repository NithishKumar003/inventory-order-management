from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.auth import get_current_user
from app.main import app


@pytest.fixture
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 10,
        "role": "customer",
    }

    def fake_get(url, headers=None, timeout=None):
        if "/products/" in url:
            return SimpleNamespace(
                status_code=200,
                json=lambda: {
                    "id": 5,
                    "name": "Test Product",
                },
            )

        if "/orders/" in url:
            return SimpleNamespace(
                status_code=200,
                json=lambda: {
                    "id": 20,
                    "user_id": 10,
                    "status": "Delivered",
                    "items": [
                        {
                            "id": 1,
                            "product_id": 5,
                            "quantity": 2,
                            "cancelled_quantity": 0,
                        }
                    ],
                },
            )

        return SimpleNamespace(status_code=404, json=lambda: {})

    monkeypatch.setattr("app.main.httpx.get", fake_get)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def review_payload():
    return {
        "product_id": 5,
        "order_id": 20,
        "rating": 5,
        "title": "Excellent product",
        "comment": "The product works very well.",
    }


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "review-service"


def test_create_review(client):
    response = client.post(
        "/reviews",
        json=review_payload(),
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
    assert response.json()["rating"] == 5
    assert response.json()["status"] == "PENDING"


def test_duplicate_review_rejected(client):
    payload = review_payload()
    headers = {"Authorization": "Bearer test-token"}

    first = client.post("/reviews", json=payload, headers=headers)
    second = client.post("/reviews", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_rating_must_be_between_one_and_five(client):
    payload = review_payload()
    payload["rating"] = 6

    response = client.post(
        "/reviews",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 422


def test_review_requires_delivered_order(client, monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        if "/products/" in url:
            return SimpleNamespace(status_code=200, json=lambda: {"id": 5})

        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "id": 20,
                "user_id": 10,
                "status": "Shipped",
                "items": [{"product_id": 5, "quantity": 1}],
            },
        )

    monkeypatch.setattr("app.main.httpx.get", fake_get)

    response = client.post(
        "/reviews",
        json=review_payload(),
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 400


def test_review_requires_product_in_order(client, monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        if "/products/" in url:
            return SimpleNamespace(status_code=200, json=lambda: {"id": 5})

        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "id": 20,
                "user_id": 10,
                "status": "Delivered",
                "items": [{"product_id": 99, "quantity": 1}],
            },
        )

    monkeypatch.setattr("app.main.httpx.get", fake_get)

    response = client.post(
        "/reviews",
        json=review_payload(),
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 400


def test_customer_cannot_moderate_reviews(client):
    response = client.get("/admin/reviews")

    assert response.status_code == 403


def test_customer_cannot_see_pending_public_reviews(client):
    headers = {"Authorization": "Bearer test-token"}

    client.post("/reviews", json=review_payload(), headers=headers)

    response = client.get("/products/5/reviews")

    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_approve_review(client):
    headers = {"Authorization": "Bearer test-token"}

    created = client.post(
        "/reviews",
        json=review_payload(),
        headers=headers,
    )

    review_id = created.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "role": "admin",
    }

    response = client.patch(
        f"/admin/reviews/{review_id}/moderation",
        json={"status": "APPROVED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


def test_approved_review_is_public(client):
    headers = {"Authorization": "Bearer test-token"}

    created = client.post(
        "/reviews",
        json=review_payload(),
        headers=headers,
    )

    review_id = created.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "role": "admin",
    }

    moderation_response = client.patch(
        f"/admin/reviews/{review_id}/moderation",
        json={"status": "APPROVED"},
    )

    assert moderation_response.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: {
        "id": 10,
        "role": "customer",
    }

    public_response = client.get("/products/5/reviews")

    assert public_response.status_code == 200
    assert len(public_response.json()) == 1
    assert public_response.json()[0]["rating"] == 5


def test_rating_summary(client):
    headers = {"Authorization": "Bearer test-token"}

    created = client.post(
        "/reviews",
        json=review_payload(),
        headers=headers,
    )

    review_id = created.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "role": "admin",
    }

    client.patch(
        f"/admin/reviews/{review_id}/moderation",
        json={"status": "APPROVED"},
    )

    response = client.get("/products/5/rating-summary")

    assert response.status_code == 200
    assert response.json()["average_rating"] == 5.0
    assert response.json()["total_reviews"] == 1