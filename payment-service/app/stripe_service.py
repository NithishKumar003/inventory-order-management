import os

import stripe
from dotenv import load_dotenv

from app.auth import SERVICE_DIR


load_dotenv(SERVICE_DIR / ".env")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)

if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is not configured.")

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(
    payment_id: int,
    order_id: int,
    amount_minor: int,
    idempotency_key: str,
    currency: str = "inr",
) -> dict:
    """Create a Stripe-hosted Checkout Session."""

    session = stripe.checkout.Session.create(
        idempotency_key=f"payment-{idempotency_key}",
        mode="payment",
        payment_method_types=["card"],
        client_reference_id=str(payment_id),
        metadata={
            "payment_id": str(payment_id),
            "order_id": str(order_id),
        },
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": f"Order #{order_id}",
                    },
                    "unit_amount": amount_minor,
                },
                "quantity": 1,
            }
        ],
        success_url=(
            f"{FRONTEND_URL}/payment/success"
            "?session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=(
            f"{FRONTEND_URL}/payment/cancel"
            f"?payment_id={payment_id}"
        ),
    )

    return {
        "session_id": session.id,
        "checkout_url": session.url,
    }

def retrieve_checkout_session(session_id: str) -> dict:
    """Retrieve an existing Stripe Checkout Session."""

    session = stripe.checkout.Session.retrieve(session_id)

    return {
        "session_id": session.id,
        "checkout_url": session.url,
    }


def verify_webhook_event(payload: bytes, signature: str) -> dict:
    """Verify a Stripe webhook signature and return its event."""

    if not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("Stripe webhook secret is not configured.")

    return stripe.Webhook.construct_event(
        payload,
        signature,
        STRIPE_WEBHOOK_SECRET,
    )
