
from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.database import SessionLocal
from app.main import app
from app.models import CartItem


def test_customer_cannot_see_another_customers_cart():
    owner_id = 910001
    other_user_id = 910002
    test_product_id = 999999

    db = SessionLocal()

    try:
        # Remove leftover records from an earlier test run.
        db.query(CartItem).filter(
            CartItem.user_id.in_([owner_id, other_user_id]),
            CartItem.product_id == test_product_id,
        ).delete(synchronize_session=False)

        # Create one cart item owned only by owner_id.
        db.add(
            CartItem(
                user_id=owner_id,
                product_id=test_product_id,
                quantity=1,
            )
        )
        db.commit()
    finally:
        db.close()

    # Authenticate the request as a different customer.
    app.dependency_overrides[get_current_user_id] = (
        lambda: other_user_id
    )

    try:
        with TestClient(app) as client:
            response = client.get("/cart")

        assert response.status_code == 200, response.text
        assert response.json()["items"] == []
        assert response.json()["item_count"] == 0

    finally:
        app.dependency_overrides.pop(
            get_current_user_id, None
        )

        db = SessionLocal()
        try:
            db.query(CartItem).filter(
                CartItem.user_id.in_([owner_id, other_user_id]),
                CartItem.product_id == test_product_id,
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
