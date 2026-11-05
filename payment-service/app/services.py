from decimal import Decimal
from uuid import uuid4
from sqlalchemy import func

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Payment, PaymentStatus, Refund, RefundStatus
from app.schemas import PaymentCreate, RefundCreate

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

def create_refund(
    refund_data: RefundCreate,
    payment_id: int,
    user_id: int,
    db: Session,
) -> Refund:
    # Check whether this idempotency key was already used.
    existing_refund = (
        db.query(Refund)
        .filter(
            Refund.user_id == user_id,
            Refund.idempotency_key == refund_data.idempotency_key,
        )
        .first()
    )

    if existing_refund:
        same_request = (
            existing_refund.payment_id == payment_id
            and existing_refund.amount == refund_data.amount
            and existing_refund.reason == refund_data.reason
        )

        if not same_request:
            raise ValueError(
                "This refund idempotency key was already used "
                "for a different request."
            )

        return existing_refund

    # Find a payment belonging to this customer.
    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == user_id,
        )
        .first()
    )

    if payment is None:
        raise LookupError("Payment not found.")

    if payment.status != PaymentStatus.SUCCESS:
        raise ValueError(
            "Only successful payments can be refunded."
        )

    # Include pending refunds to reserve their amounts.
    already_refunded = (
        db.query(func.coalesce(func.sum(Refund.amount), 0))
        .filter(
            Refund.payment_id == payment_id,
            Refund.status.in_([
                RefundStatus.PENDING,
                RefundStatus.SUCCEEDED,
            ]),
        )
        .scalar()
    )
    remaining_amount = payment.amount - Decimal(str(already_refunded))

    if refund_data.amount > remaining_amount:
        raise ValueError(
            f"Refund exceeds the remaining refundable amount "
            f"of {remaining_amount}."
        )

    # Create the refund record before contacting the provider.
    refund = Refund(
        payment_id=payment.id,
        user_id=user_id,
        amount=refund_data.amount,
        reason=refund_data.reason,
        idempotency_key=refund_data.idempotency_key,
        status=RefundStatus.PENDING,
    )

    db.add(refund)

    try:
        db.commit()
        db.refresh(refund)
    except IntegrityError:
        db.rollback()

        existing_refund = (
            db.query(Refund)
            .filter(
                Refund.user_id == user_id,
                Refund.idempotency_key == refund_data.idempotency_key,
            )
            .first()
        )

        if existing_refund:
            if (
                existing_refund.payment_id == payment_id
                and existing_refund.amount == refund_data.amount
                and existing_refund.reason == refund_data.reason
            ):
                return existing_refund

            raise ValueError(
                "This refund idempotency key was already used "
                "for a different request."
            )

        raise

    # Stripe-backed payments must be refunded through Stripe.
    if payment.stripe_session_id:
        if not payment.stripe_payment_intent_id:
            refund.status = RefundStatus.FAILED
            refund.failure_reason = (
                "Stripe PaymentIntent is not available for this payment."
            )
            db.commit()
            db.refresh(refund)
            return refund

        try:
            from app.stripe_service import create_stripe_refund

            stripe_refund = create_stripe_refund(
                payment_intent_id=payment.stripe_payment_intent_id,
                amount_minor=int(refund.amount * 100),
                idempotency_key=refund.idempotency_key,
            )

            refund.provider_reference = stripe_refund.id

            if stripe_refund.status == "succeeded":
                refund.status = RefundStatus.SUCCEEDED
            else:
                refund.status = RefundStatus.PENDING

        except Exception:
            db.rollback()

            refund = db.query(Refund).filter(
                Refund.id == refund.id
            ).first()

            refund.status = RefundStatus.FAILED
            refund.failure_reason = "Stripe refund request failed."

    else:
        # Simulated payments are refunded locally.
        refund.status = RefundStatus.SUCCEEDED
        refund.provider_reference = (
            f"SIM-REFUND-{refund.id}"
        )

    db.commit()
    db.refresh(refund)

    return refund
