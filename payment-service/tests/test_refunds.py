
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
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
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
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def successful_payment(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-REFUND-TEST",
        idempotency_key="payment-refund-test-001",
        amount=Decimal("1000.00"),
        status=PaymentStatus.SUCCESS,
    )

    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    return payment_id


def test_successful_simulated_refund(client, successful_payment):
    response = client.post(
        f"/payments/{successful_payment}/refunds",
        json={
            "amount": "300.00",
            "reason": "Customer requested refund",
            "idempotency_key": "refund-test-001",
        },
    )

    assert response.status_code == 201, response.text

    result = response.json()

    assert result["payment_id"] == successful_payment
    assert result["user_id"] == 7
    assert Decimal(result["amount"]) == Decimal("300.00")
    assert result["status"] == "SUCCEEDED"
    assert result["provider_reference"].startswith("SIM-REFUND-")


def test_refund_rejects_pending_payment(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=2,
        user_id=7,
        transaction_reference="PAY-PENDING-REFUND",
        idempotency_key="payment-pending-refund-001",
        amount=Decimal("1000.00"),
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    response = client.post(
        f"/payments/{payment_id}/refunds",
        json={
            "amount": "100.00",
            "reason": "Customer requested refund",
            "idempotency_key": "refund-pending-001",
        },
    )

    assert response.status_code == 409


def test_refund_rejects_amount_above_payment_amount(
    client, successful_payment
):
    response = client.post(
        f"/payments/{successful_payment}/refunds",
        json={
            "amount": "1200.00",
            "reason": "Refund exceeds payment",
            "idempotency_key": "refund-over-limit-001",
        },
    )

    assert response.status_code == 409


def test_refund_rejects_duplicate_idempotency_key_with_different_data(
    client, successful_payment
):
    payload = {
        "amount": "100.00",
        "reason": "Customer requested refund",
        "idempotency_key": "refund-duplicate-001",
    }

    first_response = client.post(
        f"/payments/{successful_payment}/refunds",
        json=payload,
    )

    assert first_response.status_code == 201, first_response.text

    changed_payload = {
        **payload,
        "amount": "200.00",
    }

    second_response = client.post(
        f"/payments/{successful_payment}/refunds",
        json=changed_payload,
    )

    assert second_response.status_code == 409


def test_refund_reuses_same_idempotency_request(
    client, successful_payment
):
    payload = {
        "amount": "100.00",
        "reason": "Customer requested refund",
        "idempotency_key": "refund-retry-001",
    }

    first_response = client.post(
        f"/payments/{successful_payment}/refunds",
        json=payload,
    )

    second_response = client.post(
        f"/payments/{successful_payment}/refunds",
        json=payload,
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text
    assert first_response.json()["id"] == second_response.json()["id"]


def test_refund_rejects_total_refunds_above_payment_amount(
    client, successful_payment
):
    first_response = client.post(
        f"/payments/{successful_payment}/refunds",
        json={
            "amount": "600.00",
            "reason": "First partial refund",
            "idempotency_key": "refund-partial-001",
        },
    )

    assert first_response.status_code == 201, first_response.text

    second_response = client.post(
        f"/payments/{successful_payment}/refunds",
        json={
            "amount": "500.00",
            "reason": "Second partial refund",
            "idempotency_key": "refund-partial-002",
        },
    )

    assert second_response.status_code == 409


def test_refund_rejects_payment_owned_by_another_user(client):
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=3,
        user_id=99,
        transaction_reference="PAY-OTHER-USER",
        idempotency_key="payment-other-user-001",
        amount=Decimal("1000.00"),
        status=PaymentStatus.SUCCESS,
    )

    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    response = client.post(
        f"/payments/{payment_id}/refunds",
        json={
            "amount": "100.00",
            "reason": "Customer requested refund",
            "idempotency_key": "refund-other-user-001",
        },
    )

    assert response.status_code == 404


def test_refund_rejects_nonexistent_payment(client):
    response = client.post(
        "/payments/99999/refunds",
        json={
            "amount": "100.00",
            "reason": "Customer requested refund",
            "idempotency_key": "refund-missing-001",
        },
    )

    assert response.status_code == 404


def test_refund_rejects_zero_amount(client, successful_payment):
    response = client.post(
        f"/payments/{successful_payment}/refunds",
        json={
            "amount": "0.00",
            "reason": "Invalid refund amount",
            "idempotency_key": "refund-zero-001",
        },
    )

    assert response.status_code == 422
