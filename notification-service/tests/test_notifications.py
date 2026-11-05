
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.auth import JWT_SECRET_KEY, JWT_ALGORITHM
from app.main import app

client = TestClient(app)


def create_test_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def auth_headers(user_id: int) -> dict:
    token = create_test_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_notifications_require_authentication():
    response = client.get("/notifications/")
    assert response.status_code == 401


def test_create_notification():
    response = client.post(
        "/notifications/",
        headers=auth_headers(999),
        json={
            "user_id": 999,
            "title": "Test notification",
            "message": "This is an automated test.",
            "notification_type": "TEST",
        },
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == 999


def test_user_cannot_create_notification_for_another_user():
    response = client.post(
        "/notifications/",
        headers=auth_headers(999),
        json={
            "user_id": 1000,
            "title": "Permission test",
            "message": "Testing user permissions.",
            "notification_type": "TEST",
        },
    )
    assert response.status_code == 403


def test_list_notifications():
    response = client.get(
        "/notifications/",
        headers=auth_headers(999),
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert all(item["user_id"] == 999 for item in response.json())


def test_mark_notification_as_read():
    create_response = client.post(
        "/notifications/",
        headers=auth_headers(998),
        json={
            "user_id": 998,
            "title": "Read status test",
            "message": "Testing read status.",
            "notification_type": "TEST",
        },
    )
    assert create_response.status_code == 201

    notification_id = create_response.json()["id"]

    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers=auth_headers(998),
        json={"is_read": True},
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_user_cannot_update_another_users_notification():
    create_response = client.post(
        "/notifications/",
        headers=auth_headers(998),
        json={
            "user_id": 998,
            "title": "Ownership test",
            "message": "Testing notification ownership.",
            "notification_type": "TEST",
        },
    )
    assert create_response.status_code == 201

    notification_id = create_response.json()["id"]

    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers=auth_headers(999),
        json={"is_read": True},
    )
    assert response.status_code == 404
