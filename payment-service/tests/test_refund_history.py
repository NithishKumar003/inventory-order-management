
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import Payment, PaymentStatus


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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 7}

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_successful_payment():
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-HISTORY-TEST",
        idempotency_key="payment-history-001",
        amount=Decimal("1000.00"),
        status=PaymentStatus.SUCCESS,
    )

    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    return payment_id


def test_refund_history_returns_empty_list(client):
    payment_id = create_successful_payment()

    response = client.get(
        f"/payments/{payment_id}/refunds"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_refund_history_returns_created_refund(client):
    payment_id = create_successful_payment()

    create_response = client.post(
        f"/payments/{payment_id}/refunds",
        json={
            "amount": "200.00",
            "reason": "Customer requested refund",
            "idempotency_key": "history-refund-001",
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/payments/{payment_id}/refunds"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["payment_id"] == payment_id
    assert response.json()[0]["status"] == "SUCCEEDED"


def test_refund_history_rejects_another_users_payment(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=2,
        user_id=99,
        transaction_reference="PAY-HISTORY-OTHER",
        idempotency_key="payment-history-other-001",
        amount=Decimal("1000.00"),
        status=PaymentStatus.SUCCESS,
    )

    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    response = client.get(
        f"/payments/{payment_id}/refunds"
    )

    assert response.status_code == 404


def test_refund_history_rejects_missing_payment(client):
    response = client.get("/payments/99999/refunds")

    assert response.status_code == 404