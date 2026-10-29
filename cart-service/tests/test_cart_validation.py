
from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.main import app


def test_zero_quantity_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: 1

    try:
        with TestClient(app) as client:
            response = client.post(
                "/cart/items",
                json={"product_id": 2, "quantity": 0},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


def test_negative_quantity_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: 1

    try:
        with TestClient(app) as client:
            response = client.post(
                "/cart/items",
                json={"product_id": 2, "quantity": -1},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


def test_zero_product_id_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: 1

    try:
        with TestClient(app) as client:
            response = client.post(
                "/cart/items",
                json={"product_id": 0, "quantity": 1},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
