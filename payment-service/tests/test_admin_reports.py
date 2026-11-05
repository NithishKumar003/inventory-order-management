import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import Payment, PaymentStatus, Refund, RefundStatus

@pytest.fixture
def setup_client():
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

    current_user = {"id": 1, "role": "admin"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal, current_user

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def report_data(setup_client):
    client, TestingSessionLocal, _ = setup_client

    db = TestingSessionLocal()

    payment = Payment(
        order_id=101,
        user_id=7,
        transaction_reference="PAY-ADMIN-TEST-001",
        idempotency_key="admin-payment-test-001",
        amount=Decimal("1000.00"),
        status=PaymentStatus.SUCCESS,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    refund = Refund(
        payment_id=payment.id,
        user_id=7,
        amount=Decimal("200.00"),
        reason="Admin report test",
        idempotency_key="admin-refund-test-001",
        status=RefundStatus.SUCCEEDED,
    )

    db.add(refund)
    db.commit()

    db.close()

    return client


def test_admin_can_view_all_payments(report_data):
    response = report_data.get("/admin/payments")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["order_id"] == 101
    assert response.json()[0]["status"] == "SUCCESS"


def test_admin_can_view_all_refunds(report_data):
    response = report_data.get("/admin/refunds")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["amount"] == 200.0
    assert response.json()[0]["status"] == "SUCCEEDED"


def test_customer_cannot_view_admin_reports(setup_client):
    client, _, current_user = setup_client
    current_user["role"] = "customer"

    payments_response = client.get("/admin/payments")
    refunds_response = client.get("/admin/refunds")

    assert payments_response.status_code == 403
    assert refunds_response.status_code == 403


def test_unauthenticated_user_cannot_view_admin_reports(setup_client):
    client, _, _ = setup_client

    app.dependency_overrides.pop(get_current_user, None)

    payments_response = client.get("/admin/payments")
    refunds_response = client.get("/admin/refunds")

    assert payments_response.status_code in (401, 403)
    assert refunds_response.status_code in (401, 403)