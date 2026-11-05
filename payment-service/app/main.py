
import hmac
import os

from fastapi import Depends, FastAPI, HTTPException, Request, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.models import Payment, Refund
from app.auth import get_current_user, require_admin
from app.database import (
    Base,
    engine,
    get_db,
    migrate_payment_database,
)
from app.schemas import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PaymentCreate,
    PaymentResponse,
    RefundCreate,
    RefundResponse,
    InternalRefundCreate,
)
from app.services import (
    create_payment,
    create_pending_stripe_payment,
    create_refund,
)
from app.stripe_service import (
    create_checkout_session,
    retrieve_checkout_session,
    verify_webhook_event,
)
from app.notifications import send_notification, notify_admins


Base.metadata.create_all(bind=engine)
migrate_payment_database()


app = FastAPI(
    title="Payment Service",
    description="Stripe payment processing for the Inventory and Order Management System",
    version="1.0.0",
)

bearer_scheme = HTTPBearer()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "payment-service",
    }


@app.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment_status(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["id"])

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == user_id,
        )
        .first()
    )

    if payment is None:
        return None

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "user_id": payment.user_id,
        "transaction_reference": payment.transaction_reference,
        "amount": payment.amount,
        "status": payment.status.value,
        "failure_reason": payment.failure_reason,
        "created_at": (
            payment.created_at.isoformat()
            if payment.created_at
            else None
        ),
    }

@app.get("/payments/order/{order_id}")
def get_payment_by_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(Payment)
        .filter(
            Payment.order_id == order_id,
            Payment.user_id == int(current_user["id"]),
        )
        .order_by(Payment.id.desc())
        .first()
    )

    if payment is None:
        return None

    return {
        "payment_id": payment.id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "status": payment.status.value,
        "transaction_reference": payment.transaction_reference,
        "failure_reason": payment.failure_reason,
        "created_at": (
            payment.created_at.isoformat()
            if payment.created_at
            else None
        ),
    }

@app.post("/payments/verify-session")
def verify_customer_payment_by_order(
    order_id: int,
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["id"])

    payment = (
        db.query(Payment)
        .filter(
            Payment.order_id == order_id,
            Payment.user_id == user_id,
        )
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found for this order.",
        )

    if not payment.stripe_session_id:
        raise HTTPException(
            status_code=409,
            detail="Payment has no Stripe Checkout Session.",
        )

    if session_id != payment.stripe_session_id:
        raise HTTPException(
            status_code=400,
            detail="Stripe session does not match this order.",
        )

    try:
        session = retrieve_checkout_session(
            payment.stripe_session_id
        )

        metadata = session["metadata"]

        if (
            session["session_id"] != payment.stripe_session_id
            or metadata.get("payment_id") != str(payment.id)
            or metadata.get("order_id") != str(payment.order_id)
        ):
            raise HTTPException(
                status_code=400,
                detail="Stripe session information does not match payment.",
            )

        if session["payment_status"] != "paid":
            return {
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "status": payment.status.value,
                "message": "Stripe has not confirmed payment yet.",
            }

        if (
            session["amount_total"] != int(payment.amount * 100)
            or session["currency"] != "inr"
        ):
            raise HTTPException(
                status_code=400,
                detail="Stripe amount or currency does not match payment.",
            )

        payment_intent = session["payment_intent"]

        if not payment_intent:
            raise HTTPException(
                status_code=400,
                detail="Stripe PaymentIntent is missing.",
            )

        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.SUCCESS
            payment.failure_reason = None
        elif payment.status != models.PaymentStatus.SUCCESS:
            raise HTTPException(
                status_code=409,
                detail="Payment is not in a verifiable state.",
            )

        payment.stripe_payment_intent_id = str(payment_intent)

        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment.id,
            "order_id": payment.order_id,
            "status": payment.status.value,
            "message": "Stripe payment verified successfully.",
        }

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()
        print(
            f"Customer payment verification failed: "
            f"{type(error).__name__}: {error}"
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to verify the Stripe payment.",
        ) from error
    
    
@app.post("/payments/{payment_id}/verify-session")
def verify_customer_stripe_payment(
    payment_id: int,
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["id"])

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
        raise HTTPException(
            status_code=404,
            detail="Payment not found.",
        )

    if not payment.stripe_session_id:
        raise HTTPException(
            status_code=409,
            detail="Payment has no Stripe Checkout Session.",
        )

    # Never trust a session ID supplied by the browser alone.
    if session_id != payment.stripe_session_id:
        raise HTTPException(
            status_code=400,
            detail="Stripe session does not match this payment.",
        )

    try:
        session = retrieve_checkout_session(
            payment.stripe_session_id
        )

        metadata = session["metadata"]

        if session["session_id"] != payment.stripe_session_id:
            raise HTTPException(
                status_code=400,
                detail="Stripe session ID does not match.",
            )

        if (
            metadata.get("payment_id") != str(payment.id)
            or metadata.get("order_id") != str(payment.order_id)
        ):
            raise HTTPException(
                status_code=400,
                detail="Stripe session metadata does not match payment.",
            )

        if session["payment_status"] != "paid":
            return {
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "status": payment.status.value,
                "message": "Stripe has not confirmed payment yet.",
            }

        if (
            session["amount_total"] != int(payment.amount * 100)
            or session["currency"] != "inr"
        ):
            raise HTTPException(
                status_code=400,
                detail="Stripe amount or currency does not match payment.",
            )

        payment_intent = session["payment_intent"]

        if not payment_intent:
            raise HTTPException(
                status_code=400,
                detail="Stripe PaymentIntent is missing.",
            )

        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.SUCCESS
            payment.failure_reason = None

        elif payment.status != models.PaymentStatus.SUCCESS:
            raise HTTPException(
                status_code=409,
                detail="Payment is not in a verifiable state.",
            )

        payment.stripe_payment_intent_id = str(payment_intent)

        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment.id,
            "order_id": payment.order_id,
            "status": payment.status.value,
            "message": "Stripe payment verified successfully.",
        }

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()
        print(
            f"Customer Stripe verification failed: "
            f"{type(error).__name__}: {error}"
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to verify the Stripe payment.",
        ) from error


@app.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=201,
)
def create_payment_endpoint(
    payment_data: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    try:
        user_id = int(current_user["id"])

        payment = create_payment(
            payment_data=payment_data,
            user_id=user_id,
            access_token=credentials.credentials,
            db=db,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except PermissionError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except (KeyError, TypeError) as error:
        raise HTTPException(
            status_code=502,
            detail="Authentication Service returned an invalid user.",
        ) from error

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "user_id": payment.user_id,
        "transaction_reference": payment.transaction_reference,
        "amount": payment.amount,
        "status": payment.status.value,
        "failure_reason": payment.failure_reason,
        "created_at": (
            payment.created_at.isoformat()
            if payment.created_at
            else None
        ),
    }


@app.post(
    "/payments/checkout",
    response_model=CheckoutSessionResponse,
    status_code=201,
)
def create_checkout_endpoint(
    payment_data: CheckoutSessionCreate,
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    try:
        user_id = int(current_user["id"])

        payment = create_pending_stripe_payment(
            payment_data=payment_data,
            user_id=user_id,
            access_token=credentials.credentials,
            db=db,
        )

        if payment.stripe_session_id:
            checkout = retrieve_checkout_session(
                payment.stripe_session_id
            )

            if checkout["checkout_url"]:
                return {
                    "payment_id": payment.id,
                    "session_id": checkout["session_id"],
                    "checkout_url": checkout["checkout_url"],
                }

            raise HTTPException(
                status_code=409,
                detail="The existing Stripe Checkout session has no URL.",
            )

        checkout = create_checkout_session(
            payment_id=payment.id,
            order_id=payment.order_id,
            amount_minor=int(payment.amount * 100),
            idempotency_key=payment.idempotency_key,
        )

        payment.stripe_session_id = checkout["session_id"]
        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment.id,
            "session_id": checkout["session_id"],
            "checkout_url": checkout["checkout_url"],
        }

    except HTTPException:
        raise

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except PermissionError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except (KeyError, TypeError) as error:
        db.rollback()
        print(
            f"Checkout authentication/data error: "
            f"{type(error).__name__}: {error}"
        )
        raise HTTPException(
            status_code=502,
            detail="Authentication Service returned an invalid user.",
        ) from error

    except Exception as error:
        db.rollback()
        print(
            f"Stripe Checkout creation failed: "
            f"{type(error).__name__}: {error}"
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to create or retrieve the Stripe Checkout session.",
        ) from error


@app.post("/payments/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Stripe signature.",
        )

    try:
        event = verify_webhook_event(payload, signature)

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail="Stripe webhook verification is not configured.",
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid Stripe webhook signature or payload.",
        ) from error

    event_type = event.type
    
    if event_type == "refund.updated":
        refund_data = event.data.object.to_dict()

        stripe_refund_id = refund_data.get("id")
        stripe_status = refund_data.get("status")

        if not stripe_refund_id:
            raise HTTPException(
                status_code=400,
                detail="Stripe refund ID is missing.",
            )

        refund = (
            db.query(models.Refund)
            .filter(
                models.Refund.provider_reference == stripe_refund_id
            )
            .first()
        )

        if refund is None:
            return {
                "received": True,
                "processed": False,
            }

        status_mapping = {
            "succeeded": models.RefundStatus.SUCCEEDED,
            "failed": models.RefundStatus.FAILED,
            "canceled": models.RefundStatus.FAILED,
            "pending": models.RefundStatus.PENDING,
            "requires_action": models.RefundStatus.PENDING,
        }

        new_status = status_mapping.get(stripe_status)

        if new_status is None:
            return {
                "received": True,
                "processed": False,
            }

        old_status = refund.status

        if old_status != new_status:
            refund.status = new_status
            refund.failure_reason = (
                refund_data.get("failure_reason")
                if new_status == models.RefundStatus.FAILED
                else None
            )

            db.commit()
            db.refresh(refund)

            status_text = new_status.value.lower()

            send_notification(
                user_id=refund.user_id,
                title=f"Refund {status_text}",
                message=(
                    f"Your refund #{refund.id} is {status_text}. "
                    f"Amount: ₹{refund.amount}."
                ),
                notification_type="refund_updated",
            )

            notify_admins(
                title=f"Refund {status_text}",
                message=(
                    f"Refund #{refund.id} for user "
                    f"{refund.user_id} is {status_text}. "
                    f"Amount: ₹{refund.amount}."
                ),
                notification_type="refund_updated",
            )

        return {
            "received": True,
            "processed": True,
        }

    supported_events = {
        "checkout.session.completed",
        "checkout.session.expired",
        "checkout.session.async_payment_failed",
        "refund.updated",
    }

    if event_type not in supported_events:
        return {
            "received": True,
            "processed": False,
        }

    session_data = event.data.object.to_dict()

    payment_id = session_data.get("metadata", {}).get("payment_id")
    session_id = session_data.get("id")

    if not payment_id or not session_id:
        raise HTTPException(
            status_code=400,
            detail="Checkout Session is missing payment metadata.",
        )

    try:
        payment_id = int(payment_id)

    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment ID in Checkout Session metadata.",
        ) from error

    payment = (
        db.query(models.Payment)
        .filter(
            models.Payment.id == payment_id,
            models.Payment.stripe_session_id == session_id,
        )
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment for this Checkout Session was not found.",
        )

    if event_type == "checkout.session.completed":

        if session_data.get("payment_status") != "paid":
            return {
                "received": True,
                "processed": False,
            }

        expected_amount = int(payment.amount * 100)
        stripe_amount = session_data.get("amount_total")
        stripe_currency = session_data.get("currency")

        if (
            stripe_amount != expected_amount
            or stripe_currency != "inr"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Stripe payment amount or currency does not "
                    "match the saved payment."
                ),
            )

        payment_intent = session_data.get("payment_intent")

        if isinstance(payment_intent, dict):
            payment_intent = payment_intent.get("id")

        if not payment_intent:
            raise HTTPException(
                status_code=400,
                detail="Invalid Stripe PaymentIntent reference.",
            )

        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.SUCCESS
            payment.failure_reason = None

        payment.stripe_payment_intent_id = str(payment_intent)

        db.commit()

        return {
            "received": True,
            "processed": True,
        }

    if event_type == "checkout.session.expired":

        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.CANCELLED
            payment.failure_reason = (
                "Stripe Checkout Session expired."
            )
            db.commit()

        return {
            "received": True,
            "processed": True,
        }

    if event_type == "checkout.session.async_payment_failed":

        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.FAILED
            payment.failure_reason = (
                "Stripe asynchronous payment failed."
            )
            db.commit()

        return {
            "received": True,
            "processed": True,
        }

    return {
        "received": True,
        "processed": False,
    }


@app.post("/admin/payments/{payment_id}/reconcile")
def reconcile_stripe_payment(
    payment_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found.",
        )

    if not payment.stripe_session_id:
        raise HTTPException(
            status_code=409,
            detail="Payment has no Stripe Checkout Session.",
        )

    try:
        session = retrieve_checkout_session(
            payment.stripe_session_id
        )

        metadata = session["metadata"]

        if (
            metadata.get("payment_id") != str(payment.id)
            or metadata.get("order_id") != str(payment.order_id)
        ):
            raise HTTPException(
                status_code=400,
                detail="Stripe session metadata does not match payment.",
            )

        if session["payment_status"] != "paid":
            raise HTTPException(
                status_code=409,
                detail="Stripe has not confirmed this payment as paid.",
            )

        if (
            session["amount_total"] != int(payment.amount * 100)
            or session["currency"] != "inr"
        ):
            raise HTTPException(
                status_code=400,
                detail="Stripe amount or currency does not match payment.",
            )

        payment_intent = session["payment_intent"]

        if not payment_intent:
            raise HTTPException(
                status_code=400,
                detail="Stripe PaymentIntent is missing.",
            )

        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.SUCCESS
            payment.failure_reason = None

        payment.stripe_payment_intent_id = str(payment_intent)

        db.commit()
        db.refresh(payment)

        return {
            "message": "Stripe payment reconciled successfully.",
            "payment_id": payment.id,
            "order_id": payment.order_id,
            "status": payment.status.value,
            "stripe_payment_intent_id": (
                payment.stripe_payment_intent_id
            ),
        }

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()
        print(
            f"Stripe reconciliation failed: "
            f"{type(error).__name__}: {error}"
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to verify the Stripe payment.",
        ) from error


@app.post(
    "/payments/{payment_id}/refunds",
    response_model=RefundResponse,
    status_code=201,
)
def create_refund_endpoint(
    payment_id: int,
    refund_data: RefundCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = int(current_user["id"])

        refund = create_refund(
            refund_data=refund_data,
            payment_id=payment_id,
            user_id=user_id,
            db=db,
        )

        return {
            "id": refund.id,
            "payment_id": refund.payment_id,
            "user_id": refund.user_id,
            "amount": refund.amount,
            "reason": refund.reason,
            "idempotency_key": refund.idempotency_key,
            "status": refund.status.value,
            "provider_reference": refund.provider_reference,
            "failure_reason": refund.failure_reason,
            "created_at": (
                refund.created_at.isoformat()
                if refund.created_at
                else None
            ),
        }

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except (KeyError, TypeError) as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated user.",
        ) from error


@app.get(
    "/payments/{payment_id}/refunds",
    response_model=list[RefundResponse],
)
def get_payment_refunds(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["id"])

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.user_id == user_id,
        )
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found.",
        )

    refunds = (
        db.query(Refund)
        .filter(
            Refund.payment_id == payment_id,
            Refund.user_id == user_id,
        )
        .order_by(Refund.created_at.desc())
        .all()
    )

    return [
        {
            "id": refund.id,
            "payment_id": refund.payment_id,
            "user_id": refund.user_id,
            "amount": refund.amount,
            "reason": refund.reason,
            "idempotency_key": refund.idempotency_key,
            "status": refund.status.value,
            "provider_reference": refund.provider_reference,
            "failure_reason": refund.failure_reason,
            "created_at": (
                refund.created_at.isoformat()
                if refund.created_at
                else None
            ),
        }
        for refund in refunds
    ]


@app.post(
    "/internal/refunds/by-order",
    response_model=RefundResponse,
    status_code=201,
)
def create_internal_refund(
    refund_data: InternalRefundCreate,
    x_internal_service_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    expected_token = os.getenv("INTERNAL_SERVICE_TOKEN")

    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="Internal service authentication is not configured.",
        )

    if not x_internal_service_token or not hmac.compare_digest(
        x_internal_service_token,
        expected_token,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid internal service token.",
        )

    payment = (
        db.query(Payment)
        .filter(
            Payment.order_id == refund_data.order_id,
            Payment.user_id == refund_data.user_id,
            Payment.status == models.PaymentStatus.SUCCESS,
        )
        .order_by(Payment.id.desc())
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Successful payment for this order was not found.",
        )

    try:
        refund = create_refund(
            refund_data=RefundCreate(
                amount=refund_data.amount,
                reason=refund_data.reason,
                idempotency_key=refund_data.idempotency_key,
            ),
            payment_id=payment.id,
            user_id=refund_data.user_id,
            db=db,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    return {
        "id": refund.id,
        "payment_id": refund.payment_id,
        "user_id": refund.user_id,
        "amount": refund.amount,
        "reason": refund.reason,
        "idempotency_key": refund.idempotency_key,
        "status": refund.status.value,
        "provider_reference": refund.provider_reference,
        "failure_reason": refund.failure_reason,
        "created_at": (
            refund.created_at.isoformat()
            if refund.created_at
            else None
        ),
    }


@app.get("/admin/payments")
def get_all_payments(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    payments = (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .all()
    )

    return [
        {
            "id": payment.id,
            "order_id": payment.order_id,
            "user_id": payment.user_id,
            "transaction_reference": payment.transaction_reference,
            "amount": payment.amount,
            "status": payment.status.value,
            "failure_reason": payment.failure_reason,
            "created_at": payment.created_at,
        }
        for payment in payments
    ]


@app.get("/admin/refunds")
def get_all_refunds(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    refunds = (
        db.query(Refund)
        .order_by(Refund.created_at.desc())
        .all()
    )

    return [
        {
            "id": refund.id,
            "payment_id": refund.payment_id,
            "user_id": refund.user_id,
            "amount": refund.amount,
            "reason": refund.reason,
            "idempotency_key": refund.idempotency_key,
            "status": refund.status.value,
            "provider_reference": refund.provider_reference,
            "failure_reason": refund.failure_reason,
            "created_at": refund.created_at,
        }
        for refund in refunds
    ]