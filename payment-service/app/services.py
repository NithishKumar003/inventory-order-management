from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Payment, PaymentStatus
from app.schemas import PaymentCreate

import httpx
from app.auth import ORDER_SERVICE_URL

def get_customer_order(order_id: int, access_token: str) -> dict:
    try:
        response = httpx.get(
            f"{ORDER_SERVICE_URL}/orders/{order_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5.0,
        )
    except httpx.RequestError as error:
        raise RuntimeError(
            "Order Service is unavailable. Please try again."
        ) from error

    if response.status_code == 404:
        raise LookupError(
            "Order not found or it does not belong to this customer."
        )

    if response.status_code in (401, 403):
        raise PermissionError(
            "Customer authentication failed when validating the order."
        )

    if response.status_code != 200:
        raise RuntimeError(
            "Order Service could not validate the order."
        )

    try:
        order = response.json()
        if not isinstance(order, dict):
            raise ValueError("Invalid order response")

        return order
    except (ValueError, TypeError) as error:
        raise RuntimeError(
            "Order Service returned an invalid response."
        ) from error

def create_payment(
    payment_data: PaymentCreate,
    user_id: int,
    access_token: str,
    db: Session,
) -> Payment:

    # Check whether this user has already used the idempotency key.
    existing_payment = (
        db.query(Payment)
        .filter(
            Payment.user_id == user_id,
            Payment.idempotency_key == payment_data.idempotency_key,
        )
        .first()
    )

    if existing_payment:
        same_request = (
            existing_payment.order_id == payment_data.order_id
            and existing_payment.amount == payment_data.amount
        )

        if not same_request:
            raise ValueError(
                "This idempotency key was already used for a different payment."
            )

        return existing_payment

    # Validate the order before creating a new payment.
    order = get_customer_order(
        order_id=payment_data.order_id,
        access_token=access_token,
    )

    try:
        order_user_id = int(order["user_id"])
        order_total = Decimal(str(order["total_amount"]))
        order_status = order["status"]
    except (KeyError, TypeError, ValueError):
        raise RuntimeError(
            "Order Service returned incomplete order details."
        )

    if order_user_id != user_id:
        raise LookupError(
            "Order not found or it does not belong to this customer."
        )

    if order_status in ("Cancelled", "Delivered"):
        raise ValueError(
            "Payment is not allowed for a cancelled or delivered order."
        )

    if order_total != payment_data.amount:
        raise ValueError(
            "Payment amount does not match the order total."
        )

    payment = Payment(
        order_id=payment_data.order_id,
        user_id=user_id,
        transaction_reference=f"PAY-{uuid4().hex.upper()}",
        idempotency_key=payment_data.idempotency_key,
        amount=Decimal(payment_data.amount),
        status=PaymentStatus.PENDING,
    )


    db.add(payment)

    try:
        # Save the initial transaction before simulating its outcome.
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        # Another request may have used the same key concurrently.
        db.rollback()

        existing_payment = (
            db.query(Payment)
            .filter(
                Payment.user_id == user_id,
                Payment.idempotency_key == payment_data.idempotency_key,
            )
            .first()
        )

        if existing_payment:
            same_request = (
                existing_payment.order_id == payment_data.order_id
                and existing_payment.amount == payment_data.amount
            )

            if same_request:
                return existing_payment

            raise ValueError(
                "This idempotency key was already used for a different payment."
            )

        raise

    # Simulate the payment provider's outcome.
    if payment_data.simulated_outcome == "SUCCESS":
        payment.status = PaymentStatus.SUCCESS

    elif payment_data.simulated_outcome == "FAILED":
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Simulated payment failure"

    elif payment_data.simulated_outcome == "CANCELLED":
        payment.status = PaymentStatus.CANCELLED

    db.commit()
    db.refresh(payment)

    return payment


def create_pending_stripe_payment(
    payment_data: PaymentCreate,
    user_id: int,
    access_token: str,
    db: Session,
) -> Payment:
    # Reuse the existing order validation.
    order = get_customer_order(
        order_id=payment_data.order_id,
        access_token=access_token,
    )

    try:
        order_user_id = int(order["user_id"])
        order_total = Decimal(str(order["total_amount"]))
        order_status = order["status"]
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            "Order Service returned incomplete order details."
        ) from error

    if order_user_id != user_id:
        raise LookupError(
            "Order not found or it does not belong to this customer."
        )

    if order_status in ("Cancelled", "Delivered"):
        raise ValueError(
            "Payment is not allowed for a cancelled or delivered order."
        )

    if order_total != payment_data.amount:
        raise ValueError(
            "Payment amount does not match the order total."
        )

    # Return an existing matching payment for an idempotent retry.
    existing_payment = (
        db.query(Payment)
        .filter(
            Payment.user_id == user_id,
            Payment.idempotency_key == payment_data.idempotency_key,
        )
        .first()
    )

    if existing_payment:
        same_request = (
            existing_payment.order_id == payment_data.order_id
            and existing_payment.amount == payment_data.amount
        )

        if not same_request:
            raise ValueError(
                "This idempotency key was already used for a different payment."
            )

        return existing_payment

    payment = Payment(
        order_id=payment_data.order_id,
        user_id=user_id,
        transaction_reference=f"PAY-{uuid4().hex.upper()}",
        idempotency_key=payment_data.idempotency_key,
        amount=payment_data.amount,
        status=PaymentStatus.PENDING,
    )

    db.add(payment)

    try:
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "This payment request was already processed. Retry with the same key."
        )

    return payment
