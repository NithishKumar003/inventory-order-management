
import pytest
import jwt

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db
from app.dependencies import get_db as dependency_get_db
from app.models import User
from app.security import hash_password, verify_password
from app.auth_token import JWT_SECRET_KEY, JWT_ALGORITHM


# Separate in-memory database. The real auth.db is not modified.
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


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[dependency_get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def create_user(
    email="customer@example.com",
    password="Password123!",
    role="customer",
    is_active=True,
):
    db = TestingSessionLocal()
    try:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


def login(client, email="customer@example.com", password="Password123!"):
    return client.post(
        "/login",
        json={"email": email, "password": password},
    )


# 1. Health endpoint
def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "authentication-service",
    }


# 2. Register a new user
def test_register_user(client):
    response = client.post(
        "/register",
        json={
            "email": "newuser@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "customer"
    assert data["is_active"] is True
    assert "hashed_password" not in data
    assert "password" not in data


# 3. Reject duplicate email
def test_duplicate_registration_rejected(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
    }

    first = client.post("/register", json=payload)
    second = client.post("/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


# 4. Reject invalid registration inputs
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "Password123!"},
        {"email": "short@example.com", "password": "short"},
        {"email": "missing-password@example.com"},
        {"password": "Password123!"},
    ],
)
def test_invalid_registration_rejected(client, payload):
    response = client.post("/register", json=payload)

    assert response.status_code == 422


# 5. Password is hashed, not stored as plaintext
def test_registered_password_is_hashed(client):
    password = "Password123!"

    response = client.post(
        "/register",
        json={
            "email": "hashed@example.com",
            "password": password,
        },
    )

    assert response.status_code == 201

    db = TestingSessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.email == "hashed@example.com")
            .first()
        )

        assert user is not None
        assert user.hashed_password != password
        assert verify_password(password, user.hashed_password)
    finally:
        db.close()


# 6. Successful login returns a bearer token
def test_login_success(client):
    create_user()

    response = login(client)

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20


# 7. Login token has a valid signature and subject
def test_login_token_contains_user_id(client):
    user_id = create_user()

    response = login(client)
    assert response.status_code == 200

    payload = jwt.decode(
        response.json()["access_token"],
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )

    assert payload["sub"] == str(user_id)
    assert "exp" in payload


# 8. Reject incorrect password
def test_login_wrong_password(client):
    create_user()

    response = login(client, password="WrongPassword123!")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


# 9. Reject unknown email
def test_login_unknown_email(client):
    response = login(client, email="unknown@example.com")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


# 10. Reject malformed login input
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "bad-email", "password": "Password123!"},
        {"email": "customer@example.com"},
        {"password": "Password123!"},
    ],
)
def test_invalid_login_input(client, payload):
    response = client.post("/login", json=payload)

    assert response.status_code == 422


# 11. Reject login for inactive account
def test_inactive_user_cannot_login(client):
    create_user(is_active=False)

    response = login(client)

    assert response.status_code == 403
    assert response.json()["detail"] == "This account is inactive."


# 12. Access own profile with valid token
def test_get_own_profile(client):
    create_user()

    token_response = login(client)
    token = token_response.json()["access_token"]

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "customer@example.com"
    assert response.json()["role"] == "customer"
    assert "hashed_password" not in response.json()


# 13. Reject missing bearer token
def test_profile_without_token_rejected(client):
    response = client.get("/me")

    assert response.status_code == 401


# 14. Reject malformed bearer token
def test_profile_with_invalid_token_rejected(client):
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token."


# 15. Reject expired JWT
def test_expired_token_rejected(client):
    create_user()

    from datetime import datetime, timedelta, timezone

    expired_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


# 16. Customer cannot access admin endpoint
def test_customer_denied_admin_access(client):
    create_user(role="customer")

    token = login(client).json()["access_token"]

    response = client.get(
        "/admin-test",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."


# 17. Admin can access admin endpoint
def test_admin_can_access_admin_endpoint(client):
    create_user(
        email="admin@example.com",
        role="admin",
    )

    token = login(
        client,
        email="admin@example.com",
    ).json()["access_token"]

    response = client.get(
        "/admin-test",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Administrator access granted.",
        "email": "admin@example.com",
        "role": "admin",
    }


# 18. Inactive account cannot access profile, even with a valid token
def test_inactive_user_profile_rejected(client):
    user_id = create_user(is_active=False)

    token = jwt.encode(
        {"sub": str(user_id)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


# 19. Reject a validly signed token with no subject
def test_token_without_subject_rejected(client):
    token = jwt.encode(
        {},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


# 20. Reject token referring to a nonexistent user
def test_token_for_nonexistent_user_rejected(client):
    token = jwt.encode(
        {"sub": "999999"},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
