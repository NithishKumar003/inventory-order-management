
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as payment_main
from app.database import Base, get_db
from app.main import app
from app.models import Payment, PaymentStatus


@pytest.fixture
def webhook_client():
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

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def create_test_payment(session_factory):
    db = session_factory()

    payment = Payment(
        order_id=13,
        user_id=7,
        transaction_reference="WEBHOOK-TEST-001",
        idempotency_key="webhook-test-key-001",
        amount=Decimal("191.59"),
        stripe_session_id="cs_test_webhook_001",
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    payment_id = payment.id
    db.close()

    return payment_id


def create_test_event(event_type, payment_id):
    session_data = {
        "id": "cs_test_webhook_001",
        "metadata": {
            "payment_id": str(payment_id),
            "order_id": "13",
        },
        "payment_status": "paid",
        "amount_total": 19159,
        "currency": "inr",
        "payment_intent": "pi_test_webhook_001",
    }

    return SimpleNamespace(
        type=event_type,
        data=SimpleNamespace(
            object=SimpleNamespace(
                to_dict=lambda: session_data
            )
        ),
    )


def test_completed_webhook_marks_payment_success(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        payment_id,
    )

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "processed": True,
    }

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    assert payment.status == PaymentStatus.SUCCESS
    assert payment.stripe_payment_intent_id == (
        "pi_test_webhook_001"
    )

    db.close()


def test_expired_webhook_cancels_pending_payment(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.expired",
        payment_id,
    )

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    assert payment.status == PaymentStatus.CANCELLED

    db.close()


def test_failed_webhook_marks_payment_failed(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.async_payment_failed",
        payment_id,
    )

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    assert payment.status == PaymentStatus.FAILED

    db.close()


def test_webhook_rejects_missing_signature(webhook_client):
    client, _ = webhook_client

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Missing Stripe signature."
    )


def test_webhook_rejects_invalid_signature(
    webhook_client, monkeypatch
):
    client, _ = webhook_client

    def reject_signature(payload, signature):
        raise ValueError("Invalid signature")

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        reject_signature,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers={"stripe-signature": "invalid-signature"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid Stripe webhook signature or payload."
    )
def test_duplicate_completed_webhook_is_idempotent(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        payment_id,
    )

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    headers = {"stripe-signature": "test-signature"}

    first_response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers=headers,
    )

    second_response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    assert payment.status == PaymentStatus.SUCCESS
    assert payment.stripe_payment_intent_id == (
        "pi_test_webhook_001"
    )

    assert db.query(Payment).count() == 1

    db.close()
def test_completed_webhook_rejects_wrong_amount(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        payment_id,
    )

    event.data.object.to_dict()["amount_total"] = 99999

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 400
    assert "amount or currency" in response.json()["detail"]

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    assert payment.status == PaymentStatus.PENDING

    db.close()
def test_completed_webhook_rejects_wrong_currency(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        payment_id,
    )

    event.data.object.to_dict()["currency"] = "usd"

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 400
    assert "amount or currency" in response.json()["detail"]

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    assert payment.status == PaymentStatus.PENDING

    db.close()
    
def test_webhook_rejects_missing_payment_metadata(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        1,
    )

    event.data.object.to_dict()["metadata"] = {
        "order_id": "13"
    }

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test webhook payload",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Checkout Session is missing payment metadata."
    )

    db = session_factory()
    payment = db.query(Payment).first()

    assert payment.status == PaymentStatus.PENDING

    db.close()
def test_webhook_rejects_unknown_payment(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        9999,
    )

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 404


def test_webhook_rejects_missing_payment_intent(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        payment_id,
    )
    event.data.object.to_dict()["payment_intent"] = None

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 400

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()
    assert payment.status == PaymentStatus.PENDING
    db.close()


def test_unpaid_completed_event_does_not_update_payment(
    webhook_client, monkeypatch
):
    client, session_factory = webhook_client
    payment_id = create_test_payment(session_factory)

    event = create_test_event(
        "checkout.session.completed",
        payment_id,
    )
    event.data.object.to_dict()["payment_status"] = "unpaid"

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "processed": False,
    }

    db = session_factory()
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()
    assert payment.status == PaymentStatus.PENDING
    db.close()


def test_unrecognized_event_is_ignored(
    webhook_client, monkeypatch
):
    client, _ = webhook_client

    event = SimpleNamespace(type="customer.created")

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        lambda payload, signature: event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"test",
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "processed": False,
    }