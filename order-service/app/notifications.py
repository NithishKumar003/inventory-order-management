import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVICE_DIR / ".env")

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://127.0.0.1:8007",
)

INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")


def send_notification(
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    reference: str = "notification",
):
    if not INTERNAL_SERVICE_TOKEN:
        logger.error(
            "Cannot send %s: internal service token is not configured.",
            reference,
        )
        return

    notification_data = {
        "user_id": user_id,
        "title": title,
        "message": message,
        "notification_type": notification_type,
    }

    try:
        response = httpx.post(
            f"{NOTIFICATION_SERVICE_URL}/notifications/internal",
            json=notification_data,
            headers={
                "X-Internal-Service-Token": INTERNAL_SERVICE_TOKEN,
            },
            timeout=5.0,
        )

        response.raise_for_status()

        logger.info("Notification sent successfully: %s", reference)

    except Exception:
        logger.exception("Could not send notification: %s", reference)


def send_order_notification(
    user_id: int,
    order_number: str,
    total_amount,
    access_token: str | None = None,
):
    send_notification(
        user_id=user_id,
        title="Order placed successfully",
        message=(
            f"Your order {order_number} has been placed successfully. "
            f"Order total: {total_amount}."
        ),
        notification_type="order_created",
        reference=f"order {order_number}",
    )