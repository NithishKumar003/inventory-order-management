from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.database import Base, engine, get_db
from app.schemas import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PaymentCreate,
    PaymentResponse,
)
from app.services import create_payment, create_pending_stripe_payment
from app.stripe_service import (
    create_checkout_session,
    retrieve_checkout_session,
    verify_webhook_event,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Payment Service",
    description="Simulated payments for the Inventory and Order Management System",
    version="1.0.0",
)

bearer_scheme = HTTPBearer()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "payment-service",
    }

@app.post("/payments", response_model=PaymentResponse, status_code=201)
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

    except (KeyError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Authentication Service returned an invalid user.",
        )

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

        # Reuse the existing Stripe session for repeated requests.
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

    except Exception as error:
        db.rollback()
        print(f"Stripe Checkout creation failed: {type(error).__name__}")
        raise HTTPException(
            status_code=502,
            detail="Unable to create or retrieve the Stripe Checkout session.",
        ) from error

    except (KeyError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Authentication Service returned an invalid user.",
        )


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

    event_type = event.get("type")

    # Ignore event types this service does not process.
    supported_events = {
        "checkout.session.completed",
        "checkout.session.expired",
        "checkout.session.async_payment_failed",
    }

    if event_type not in supported_events:
        return {"received": True, "processed": False}

    session_data = event.get("data", {}).get("object", {})

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

    # A completed session counts as successful only when Stripe
    # confirms payment and the amount and currency match.
    if event_type == "checkout.session.completed":
        if session_data.get("payment_status") != "paid":
            return {"received": True, "processed": False}

        expected_amount = int(payment.amount * 100)
        stripe_amount = session_data.get("amount_total")
        stripe_currency = session_data.get("currency")

        if stripe_amount != expected_amount or stripe_currency != "inr":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Stripe payment amount or currency does not "
                    "match the saved payment."
                ),
            )

        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.SUCCESS
            payment.failure_reason = None
            db.commit()

        return {"received": True, "processed": True}

    # Expired sessions cancel only payments still pending.
    if event_type == "checkout.session.expired":
        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.CANCELLED
            payment.failure_reason = "Stripe Checkout Session expired."
            db.commit()

        return {"received": True, "processed": True}

    # Failed asynchronous payments update only pending payments.
    if event_type == "checkout.session.async_payment_failed":
        if payment.status == models.PaymentStatus.PENDING:
            payment.status = models.PaymentStatus.FAILED
            payment.failure_reason = (
                "Stripe asynchronous payment failed."
            )
            db.commit()

        return {"received": True, "processed": True}

    return {"received": True, "processed": False}
