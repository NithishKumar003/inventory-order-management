
import os
import hmac

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from .auth import get_current_user_id
from .database import get_db
from .models import Notification
from .rabbitmq import publish_notification
from .schemas import (
    NotificationCreate,
    NotificationReadUpdate,
    NotificationResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def save_and_publish_notification(
    notification_data: NotificationCreate,
    db: Session,
):
    notification = Notification(**notification_data.model_dump())

    try:
        db.add(notification)
        db.commit()
        db.refresh(notification)

        publish_notification({
            "notification_id": notification.id,
        })

        return notification

    except Exception as error:
        db.rollback()

        if notification.id is not None:
            db.delete(notification)
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification service is temporarily unavailable.",
        ) from error


@router.post(
    "/",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if notification_data.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can create notifications only for yourself.",
        )

    return save_and_publish_notification(notification_data, db)


@router.post(
    "/internal",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_internal_notification(
    notification_data: NotificationCreate,
    service_token: str | None = Header(
        default=None,
        alias="X-Internal-Service-Token",
    ),
    db: Session = Depends(get_db),
):
    expected_token = os.getenv("INTERNAL_SERVICE_TOKEN")

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal service authentication is not configured.",
        )

    if not service_token or not hmac.compare_digest(
        service_token,
        expected_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service credentials.",
        )

    return save_and_publish_notification(notification_data, db)


@router.get("/", response_model=list[NotificationResponse])
def list_notifications(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def update_notification_read_status(
    notification_id: int,
    update_data: NotificationReadUpdate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user_id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    notification.is_read = update_data.is_read
    db.commit()
    db.refresh(notification)

    return notification
