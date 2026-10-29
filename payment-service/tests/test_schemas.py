
import pytest
from pydantic import ValidationError

from app.schemas import PaymentCreate


def test_valid_payment_request():
    payment = PaymentCreate(
        order_id=1,
        amount="1250.00",
        idempotency_key="payment-test-001",
        simulated_outcome="SUCCESS",
    )

    assert payment.order_id == 1
    assert payment.amount == 1250
    assert payment.simulated_outcome == "SUCCESS"


@pytest.mark.parametrize("order_id", [0, -1])
def test_invalid_order_id(order_id):
    with pytest.raises(ValidationError):
        PaymentCreate(
            order_id=order_id,
            amount="1250.00",
            idempotency_key="payment-test-001",
        )


@pytest.mark.parametrize("amount", ["0", "-10.00"])
def test_invalid_payment_amount(amount):
    with pytest.raises(ValidationError):
        PaymentCreate(
            order_id=1,
            amount=amount,
            idempotency_key="payment-test-001",
        )


def test_idempotency_key_too_short():
    with pytest.raises(ValidationError):
        PaymentCreate(
            order_id=1,
            amount="100.00",
            idempotency_key="short",
        )


def test_unsupported_payment_outcome():
    with pytest.raises(ValidationError):
        PaymentCreate(
            order_id=1,
            amount="100.00",
            idempotency_key="payment-test-002",
            simulated_outcome="REFUNDED",
        )
