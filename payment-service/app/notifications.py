import logging
import os

import httpx

logger = logging.getLogger(__name__)

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://notification-service:8007",
)

AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL",
    "http://auth-service:8001",
)

INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN",
    "",
)


def send_notification(
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
):
    if not INTERNAL_SERVICE_TOKEN:
        logger.error("Internal service token is not configured.")
        return

    try:
        response = httpx.post(
            f"{NOTIFICATION_SERVICE_URL}/notifications/internal",
            json={
                "user_id": user_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
            },
            headers={
                "X-Internal-Service-Token": INTERNAL_SERVICE_TOKEN,
            },
            timeout=5.0,
        )
        response.raise_for_status()

    except Exception:
        logger.exception(
            "Could not send notification to user %s.",
            user_id,
        )


def notify_admins(
    title: str,
    message: str,
    notification_type: str,
):
    if not INTERNAL_SERVICE_TOKEN:
        logger.error("Internal service token is not configured.")
        return

    try:
        response = httpx.get(
            f"{AUTH_SERVICE_URL}/internal/admin-ids",
            headers={
                "X-Internal-Service-Token": INTERNAL_SERVICE_TOKEN,
            },
            timeout=5.0,
        )
        response.raise_for_status()

        admin_ids = response.json().get("admin_ids", [])

        for admin_id in admin_ids:
            send_notification(
                user_id=admin_id,
                title=title,
                message=message,
                notification_type=notification_type,
            )

    except Exception:
        logger.exception("Could not notify administrators.")