
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as payment_main
from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import Payment


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


def test_checkout_schema_rejects_invalid_amount():
    from app.schemas import CheckoutSessionCreate

    with pytest.raises(ValueError):
        CheckoutSessionCreate(
            order_id=1,
            amount="0.00",
            idempotency_key="payment-test-001",
        )


def test_checkout_endpoint_is_registered():
    routes = {
        route.path
        for route in app.routes
        if hasattr(route, "path")
    }

    assert "/payments/checkout" in routes


def test_checkout_creates_pending_payment_and_stripe_session(
    client, monkeypatch
):
    def fake_get_customer_order(order_id, access_token):
        assert order_id == 1
        assert access_token == "test-token"
        return {
            "id": 1,
            "user_id": 7,
            "total_amount": "1250.00",
            "status": "Confirmed",
        }

    def fake_create_checkout_session(
        payment_id,
        order_id,
        amount_minor,
        idempotency_key,
        currency="inr",
    ):
        assert payment_id > 0
        assert order_id == 1
        assert amount_minor == 125000
        assert idempotency_key == "payment-test-001"
        return {
            "session_id": "cs_test_mock123",
            "checkout_url": "https://checkout.stripe.test/session123",
        }

    import app.services as payment_services

    monkeypatch.setattr(
        payment_services,
        "get_customer_order",
        fake_get_customer_order,
    )
    monkeypatch.setattr(
        payment_main,
        "create_checkout_session",
        fake_create_checkout_session,
    )

    response = client.post(
        "/payments/checkout",
        headers={"Authorization": "Bearer test-token"},
        json={
            "order_id": 1,
            "amount": "1250.00",
            "idempotency_key": "payment-test-001",
        },
    )

    assert response.status_code == 201, response.text

    result = response.json()
    assert result["payment_id"] > 0
    assert result["session_id"] == "cs_test_mock123"
    assert result["checkout_url"] == (
        "https://checkout.stripe.test/session123"
    )

    from app.database import get_db

    # The payment should remain pending until a verified webhook confirms
    # that Stripe actually received the payment.
    assert result["payment_id"] > 0


def test_checkout_reuses_existing_stripe_session(client, monkeypatch):
    import app.services as payment_services
    from app.models import Payment, PaymentStatus
    from app.database import SessionLocal

    def fake_get_customer_order(order_id, access_token):
        return {
            "id": order_id,
            "user_id": 7,
            "total_amount": "1250.00",
            "status": "Confirmed",
        }

    monkeypatch.setattr(
        payment_services,
        "get_customer_order",
        fake_get_customer_order,
    )

    # Create a payment with an existing Stripe session in the test DB.
    db = next(
        app.dependency_overrides[
            __import__("app.database", fromlist=["get_db"]).get_db
        ]()
    )
    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-REUSE-TEST",
        idempotency_key="payment-test-001",
        amount=Decimal("1250.00"),
        status=PaymentStatus.PENDING,
        stripe_session_id="cs_test_existing123",
    )
    db.add(payment)
    db.commit()
    db.close()

    def fake_retrieve_checkout_session(session_id):
        assert session_id == "cs_test_existing123"
        return {
            "session_id": session_id,
            "checkout_url": "https://checkout.stripe.test/existing",
        }

    def fail_create_checkout_session(**kwargs):
        pytest.fail("A new Stripe session should not be created.")

    monkeypatch.setattr(
        payment_main,
        "retrieve_checkout_session",
        fake_retrieve_checkout_session,
    )
    monkeypatch.setattr(
        payment_main,
        "create_checkout_session",
        fail_create_checkout_session,
    )

    response = client.post(
        "/payments/checkout",
        headers={"Authorization": "Bearer test-token"},
        json={
            "order_id": 1,
            "amount": "1250.00",
            "idempotency_key": "payment-test-001",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["session_id"] == "cs_test_existing123"
    assert response.json()["checkout_url"] == (
        "https://checkout.stripe.test/existing"
    )

def test_webhook_rejects_missing_signature(client):
    response = client.post(
        "/payments/webhook",
        content=b"{}",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Stripe signature."


def test_webhook_rejects_invalid_signature(client, monkeypatch):
    def fake_verify_webhook_event(payload, signature):
        raise ValueError("Invalid signature")

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        fake_verify_webhook_event,
    )

    response = client.post(
        "/payments/webhook",
        content=b"{}",
        headers={"stripe-signature": "invalid-signature"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid Stripe webhook signature or payload."
    )


def test_webhook_marks_matching_paid_payment_successful(
    client, monkeypatch
):
    from app.models import PaymentStatus

    # Create a pending payment in the test database.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-WEBHOOK-TEST",
        idempotency_key="payment-webhook-001",
        amount=Decimal("1250.00"),
        status=PaymentStatus.PENDING,
        stripe_session_id="cs_test_webhook123",
    )
    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    # Simulate a verified Stripe webhook event.
    def fake_verify_webhook_event(payload, signature):
        assert payload == b'{"test":"event"}'
        assert signature == "test-signature"

        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_webhook123",
                    "payment_status": "paid",
                    "amount_total": 125000,
                    "currency": "inr",
                    "metadata": {
                        "payment_id": str(payment_id),
                    },
                },
            },
        }

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        fake_verify_webhook_event,
    )

    response = client.post(
        "/payments/webhook",
        content=b'{"test":"event"}',
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "received": True,
        "processed": True,
    }

    # Verify that the payment was marked successful.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    saved_payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    assert saved_payment.status == PaymentStatus.SUCCESS

    db.close()
    db_generator.close()


def test_webhook_rejects_mismatched_amount(
    client, monkeypatch
):
    from app.models import PaymentStatus

    # Create a pending payment worth ₹1,250.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-WEBHOOK-WRONG-AMOUNT",
        idempotency_key="payment-webhook-wrong-001",
        amount=Decimal("1250.00"),
        status=PaymentStatus.PENDING,
        stripe_session_id="cs_test_wrong_amount",
    )
    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    # Stripe reports ₹100 instead of the expected ₹1,250.
    def fake_verify_webhook_event(payload, signature):
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_wrong_amount",
                    "payment_status": "paid",
                    "amount_total": 10000,
                    "currency": "inr",
                    "metadata": {
                        "payment_id": str(payment_id),
                    },
                },
            },
        }

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        fake_verify_webhook_event,
    )

    response = client.post(
        "/payments/webhook",
        content=b'{"test":"wrong-amount"}',
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Stripe payment amount or currency does not match the saved payment."
    )

    # Confirm the rejected event did not change the payment.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    saved_payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    assert saved_payment.status == PaymentStatus.PENDING

    db.close()
    db_generator.close()


def test_webhook_rejects_wrong_currency(
    client, monkeypatch
):
    from app.models import PaymentStatus

    # Create a pending payment for ₹1,250.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-WEBHOOK-WRONG-CURRENCY",
        idempotency_key="payment-webhook-currency-001",
        amount=Decimal("1250.00"),
        status=PaymentStatus.PENDING,
        stripe_session_id="cs_test_wrong_currency",
    )
    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    # Simulate Stripe reporting USD instead of INR.
    def fake_verify_webhook_event(payload, signature):
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_wrong_currency",
                    "payment_status": "paid",
                    "amount_total": 125000,
                    "currency": "usd",
                    "metadata": {
                        "payment_id": str(payment_id),
                    },
                },
            },
        }

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        fake_verify_webhook_event,
    )

    response = client.post(
        "/payments/webhook",
        content=b'{"test":"wrong-currency"}',
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Stripe payment amount or currency does not match the saved payment."
    )

    # Confirm the payment remains pending.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    saved_payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    assert saved_payment.status == PaymentStatus.PENDING

    db.close()
    db_generator.close()

def test_webhook_cancels_pending_payment_when_session_expires(
    client, monkeypatch
):
    from app.models import PaymentStatus

    # Create a pending payment.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-WEBHOOK-EXPIRED",
        idempotency_key="payment-webhook-expired-001",
        amount=Decimal("1250.00"),
        status=PaymentStatus.PENDING,
        stripe_session_id="cs_test_expired123",
    )
    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    # Simulate a verified Stripe expiration event.
    def fake_verify_webhook_event(payload, signature):
        return {
            "type": "checkout.session.expired",
            "data": {
                "object": {
                    "id": "cs_test_expired123",
                    "metadata": {
                        "payment_id": str(payment_id),
                    },
                },
            },
        }

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        fake_verify_webhook_event,
    )

    response = client.post(
        "/payments/webhook",
        content=b'{"test":"expired"}',
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "received": True,
        "processed": True,
    }

    # Confirm the pending payment is now cancelled.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    saved_payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    assert saved_payment.status == PaymentStatus.CANCELLED
    assert saved_payment.failure_reason == (
        "Stripe Checkout Session expired."
    )

    db.close()
    db_generator.close()

def test_webhook_marks_pending_payment_failed_async(
    client, monkeypatch
):
    from app.models import PaymentStatus

    # Create a pending payment.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-WEBHOOK-ASYNC-FAILED",
        idempotency_key="payment-webhook-async-failed-001",
        amount=Decimal("1250.00"),
        status=PaymentStatus.PENDING,
        stripe_session_id="cs_test_async_failed123",
    )
    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    # Simulate a verified Stripe asynchronous payment failure.
    def fake_verify_webhook_event(payload, signature):
        return {
            "type": "checkout.session.async_payment_failed",
            "data": {
                "object": {
                    "id": "cs_test_async_failed123",
                    "metadata": {
                        "payment_id": str(payment_id),
                    },
                },
            },
        }

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        fake_verify_webhook_event,
    )

    response = client.post(
        "/payments/webhook",
        content=b'{"test":"async-failed"}',
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "received": True,
        "processed": True,
    }

    # Confirm the payment is marked failed.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    saved_payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    assert saved_payment.status == PaymentStatus.FAILED
    assert saved_payment.failure_reason == (
        "Stripe asynchronous payment failed."
    )

    db.close()
    db_generator.close()

def test_webhook_does_not_cancel_already_successful_payment(
    client, monkeypatch
):
    from app.models import PaymentStatus

    # Create a payment that has already succeeded.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    payment = Payment(
        order_id=1,
        user_id=7,
        transaction_reference="PAY-WEBHOOK-ALREADY-SUCCESS",
        idempotency_key="payment-webhook-already-success-001",
        amount=Decimal("1250.00"),
        status=PaymentStatus.SUCCESS,
        stripe_session_id="cs_test_already_success123",
    )
    db.add(payment)
    db.commit()
    payment_id = payment.id

    db.close()
    db_generator.close()

    # Simulate a late expiration event for the same session.
    def fake_verify_webhook_event(payload, signature):
        return {
            "type": "checkout.session.expired",
            "data": {
                "object": {
                    "id": "cs_test_already_success123",
                    "metadata": {
                        "payment_id": str(payment_id),
                    },
                },
            },
        }

    monkeypatch.setattr(
        payment_main,
        "verify_webhook_event",
        fake_verify_webhook_event,
    )

    response = client.post(
        "/payments/webhook",
        content=b'{"test":"late-expiration"}',
        headers={"stripe-signature": "test-signature"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "received": True,
        "processed": True,
    }

    # Verify the successful payment was not cancelled.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    saved_payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    assert saved_payment.status == PaymentStatus.SUCCESS
    assert saved_payment.failure_reason is None

    db.close()
    db_generator.close()
