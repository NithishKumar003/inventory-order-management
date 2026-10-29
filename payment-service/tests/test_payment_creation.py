from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services as payment_services
from app.database import Base
from app.models import Payment, PaymentStatus
from app.schemas import PaymentCreate


@pytest.fixture
def db_session():
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

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def mock_order(monkeypatch, order_data):
    def fake_get_customer_order(order_id, access_token):
        return order_data

    monkeypatch.setattr(
        payment_services,
        "get_customer_order",
        fake_get_customer_order,
    )


def valid_payment_data(**overrides):
    data = {
        "order_id": 1,
        "amount": "1250.00",
        "idempotency_key": "payment-test-001",
        "simulated_outcome": "SUCCESS",
    }
    data.update(overrides)
    return PaymentCreate(**data)


def test_reject_payment_for_another_users_order(
    db_session, monkeypatch
):
    mock_order(
        monkeypatch,
        {
            "user_id": 99,
            "total_amount": "1250.00",
            "status": "Confirmed",
        },
    )

    with pytest.raises(LookupError, match="does not belong"):
        payment_services.create_payment(
            payment_data=valid_payment_data(),
            user_id=7,
            access_token="test-token",
            db=db_session,
        )

    assert db_session.query(Payment).count() == 0


def test_reject_payment_when_amount_does_not_match(
    db_session, monkeypatch
):
    mock_order(
        monkeypatch,
        {
            "user_id": 7,
            "total_amount": "1500.00",
            "status": "Confirmed",
        },
    )

    with pytest.raises(ValueError, match="does not match"):
        payment_services.create_payment(
            payment_data=valid_payment_data(),
            user_id=7,
            access_token="test-token",
            db=db_session,
        )

    assert db_session.query(Payment).count() == 0


@pytest.mark.parametrize("order_status", ["Cancelled", "Delivered"])
def test_reject_payment_for_ineligible_order_status(
    db_session, monkeypatch, order_status
):
    mock_order(
        monkeypatch,
        {
            "user_id": 7,
            "total_amount": "1250.00",
            "status": order_status,
        },
    )

    with pytest.raises(ValueError, match="not allowed"):
        payment_services.create_payment(
            payment_data=valid_payment_data(),
            user_id=7,
            access_token="test-token",
            db=db_session,
        )

    assert db_session.query(Payment).count() == 0


def test_create_successful_payment(db_session, monkeypatch):
    mock_order(
        monkeypatch,
        {
            "user_id": 7,
            "total_amount": "1250.00",
            "status": "Confirmed",
        },
    )

    payment = payment_services.create_payment(
        payment_data=valid_payment_data(),
        user_id=7,
        access_token="test-token",
        db=db_session,
    )

    assert payment.id is not None
    assert payment.order_id == 1
    assert payment.user_id == 7
    assert payment.amount == Decimal("1250.00")
    assert payment.status == PaymentStatus.SUCCESS
    assert payment.transaction_reference.startswith("PAY-")
