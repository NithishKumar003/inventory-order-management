
import hmac
from dotenv import load_dotenv
import os
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.notifications import send_notification, notify_admins

from app.auth import get_current_user
from app.database import (
    Base,
    engine,
    get_db,
    migrate_return_database,
)
from app.models import ReturnRequest
from app.schemas import (
    ReturnCreate,
    ReturnModeration,
    ReturnResponse,
)

load_dotenv()

PAYMENT_SERVICE_URL = os.getenv(
    "PAYMENT_SERVICE_URL",
    "http://127.0.0.1:8006",
)

INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")

ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL",
    "http://127.0.0.1:8005",
)

Base.metadata.create_all(bind=engine)
migrate_return_database()

app = FastAPI(
    title="Return Management Service",
    version="1.0.0",
)


def get_order(order_id: int, token: str):
    try:
        response = httpx.get(
            f"{ORDER_SERVICE_URL}/orders/{order_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        response.raise_for_status()
        return response.json()

    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Order service is unavailable.",
        )
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="Unable to verify the order.",
        )


def require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required.",
        )


@app.get("/health")
def health():
    return {
        "service": "return-service",
        "status": "healthy",
    }


@app.post(
    "/returns",
    response_model=ReturnResponse,
    status_code=201,
)
def create_return(
    return_data: ReturnCreate,
    credentials=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(credentials["id"])

    # Return an existing request for an identical retry.
    existing = (
        db.query(ReturnRequest)
        .filter(
            ReturnRequest.user_id == user_id,
            ReturnRequest.idempotency_key
            == return_data.idempotency_key,
        )
        .first()
    )

    if existing:
        same_request = (
            existing.order_id == return_data.order_id
            and existing.order_item_id == return_data.order_item_id
            and existing.quantity == return_data.quantity
            and existing.reason == return_data.reason
        )

        if not same_request:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key was already used for another request.",
            )

        return existing

    token = credentials.get("_access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication token is missing.",
        )

    # Verify the order with Order Service.
    order = get_order(return_data.order_id, token)

    if order.get("user_id") != user_id:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    # The overall order must be delivered.
    if order.get("status") != "Delivered":
        raise HTTPException(
            status_code=409,
            detail="Only delivered orders can be returned.",
        )

    # Find the requested item inside this order.
    order_item = next(
        (
            item
            for item in order.get("items", [])
            if item.get("id") == return_data.order_item_id
        ),
        None,
    )

    if order_item is None:
        raise HTTPException(
            status_code=404,
            detail="Order item not found.",
        )

    # Do not require the individual item status to be Delivered.
    # The order-level Delivered status is checked above.

    if order_item.get("product_id", 0) <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid product information in order.",
        )

    # Calculate refund amount using item unit price.
    try:
        unit_price = Decimal(str(order_item["unit_price"]))

        if not unit_price.is_finite() or unit_price <= 0:
            raise ValueError("Invalid unit price.")

        refund_amount = unit_price * return_data.quantity

    except (KeyError, TypeError, ValueError, InvalidOperation):
        raise HTTPException(
            status_code=502,
            detail="Unable to calculate the return refund amount.",
        )

    # Check how many units are eligible for return.
    available_quantity = (
        order_item["quantity"] - order_item["cancelled_quantity"]
    )

    already_requested = (
        db.query(ReturnRequest)
        .filter(
            ReturnRequest.order_item_id == return_data.order_item_id,
            ReturnRequest.status.in_(
                ["PENDING", "APPROVED", "COMPLETED"]
            ),
        )
        .all()
    )

    already_returned_quantity = sum(
        item.quantity for item in already_requested
    )

    remaining_quantity = (
        available_quantity - already_returned_quantity
    )

    if return_data.quantity > remaining_quantity:
        raise HTTPException(
            status_code=409,
            detail="Return quantity exceeds the remaining eligible quantity.",
        )

    # Save the return request and calculated refund amount.
    return_request = ReturnRequest(
        user_id=user_id,
        order_id=return_data.order_id,
        order_item_id=return_data.order_item_id,
        product_id=order_item["product_id"],
        quantity=return_data.quantity,
        reason=return_data.reason,
        idempotency_key=return_data.idempotency_key,
        status="PENDING",
        refund_amount=refund_amount,
        refund_status="NOT_STARTED",
    )

    try:
        db.add(return_request)
        db.commit()
        db.refresh(return_request)
        
        send_notification(
            user_id=return_request.user_id,
            title="Return request submitted",
            message=f"Your return request #{return_request.id} has been submitted and is awaiting review.",
            notification_type="return_created",
        )

        notify_admins(
            title="New return request",
            message=f"Return request #{return_request.id} requires review.",
            notification_type="return_created",
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A return request with this key already exists.",
        )

    return return_request


@app.get(
    "/returns/me",
    response_model=list[ReturnResponse],
)
def get_my_returns(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(ReturnRequest)
        .filter(
            ReturnRequest.user_id == int(current_user["id"])
        )
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )


@app.get(
    "/returns/admin",
    response_model=list[ReturnResponse],
)
def get_all_returns(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    return (
        db.query(ReturnRequest)
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )


@app.patch(
    "/returns/admin/{return_id}/moderation",
    response_model=ReturnResponse,
)
def moderate_return(
    return_id: int,
    moderation: ReturnModeration,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    return_request = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .first()
    )

    if return_request is None:
        raise HTTPException(
            status_code=404,
            detail="Return request not found.",
        )

    if return_request.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="Only pending return requests can be reviewed.",
        )

    return_request.status = moderation.status
    return_request.admin_note = moderation.admin_note

    db.commit()
    db.refresh(return_request)
    
    send_notification(
        user_id=return_request.user_id,
        title=f"Return request {moderation.status.lower()}",
        message=(
            f"Your return request #{return_request.id} "
            f"has been {moderation.status.lower()}."
        ),
        notification_type="return_updated",
    )

    return return_request


@app.post(
    "/returns/admin/{return_id}/complete",
    response_model=ReturnResponse,
)
def complete_return(
    return_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    return_request = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .first()
    )

    if return_request is None:
        raise HTTPException(
            status_code=404,
            detail="Return request not found.",
        )

    if return_request.status == "COMPLETED":
        return return_request

    if return_request.status != "APPROVED":
        raise HTTPException(
            status_code=409,
            detail="Only approved returns can be completed.",
        )

    if return_request.refund_status == "SUCCEEDED":
        return_request.status = "COMPLETED"
        db.commit()
        db.refresh(return_request)

        send_notification(
            user_id=return_request.user_id,
            title="Refund succeeded",
            message=(
                f"Refund for return request #{return_request.id} "
                f"was successful. Amount: ₹{return_request.refund_amount}."
            ),
            notification_type="refund_updated",
        )

        notify_admins(
            title="Return refund succeeded",
            message=f"Return request #{return_request.id} has been completed.",
            notification_type="refund_updated",
        )

        return return_request

    if not INTERNAL_SERVICE_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Internal payment service authentication is not configured.",
        )

    if return_request.refund_amount is None or return_request.refund_amount <= 0:
        raise HTTPException(
            status_code=409,
            detail="A valid refund amount is required.",
        )

    payload = {
        "order_id": return_request.order_id,
        "user_id": return_request.user_id,
        "amount": str(return_request.refund_amount),
        "reason": f"Return approved: {return_request.reason}"[:250],
        "idempotency_key": f"return-{return_request.id}",
    }

    try:
        response = httpx.post(
            f"{PAYMENT_SERVICE_URL}/internal/refunds/by-order",
            json=payload,
            headers={
                "X-Internal-Service-Token": INTERNAL_SERVICE_TOKEN,
            },
            timeout=10.0,
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Payment service is unavailable. You can retry this return.",
        )

    if response.status_code >= 400:
        if response.status_code in (401, 403, 500):
            raise HTTPException(
                status_code=502,
                detail="Payment service authentication or configuration failed.",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=409,
                detail="No successful payment was found for this order.",
            )

        raise HTTPException(
            status_code=502,
            detail="The payment service could not process the refund.",
        )

    try:
        refund_data = response.json()
        refund_id = int(refund_data["id"])
        refund_status = str(refund_data["status"]).upper()
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=502,
            detail="The payment service returned an invalid refund response.",
        )

    if refund_status not in {"SUCCEEDED", "PENDING", "FAILED"}:
        raise HTTPException(
            status_code=502,
            detail="The payment service returned an unknown refund status.",
        )

    return_request.payment_refund_id = refund_id
    return_request.refund_status = refund_status

    if refund_status == "SUCCEEDED":
        return_request.status = "COMPLETED"
        return_request.refund_failure_reason = None

    elif refund_status == "PENDING":
        return_request.refund_failure_reason = None

    else:
        return_request.refund_failure_reason = (
            refund_data.get("failure_reason")
            or "The payment provider reported that the refund failed."
        )

    db.commit()
    db.refresh(return_request)
    
    send_notification(
        user_id=return_request.user_id,
        title=f"Refund {refund_status.lower()}",
        message=(
            f"Refund for return request #{return_request.id} "
            f"is {refund_status.lower()}. "
            f"Amount: ₹{return_request.refund_amount}."
        ),
        notification_type="refund_updated",
    )
    
    notify_admins(
        title=f"Return refund {refund_status.lower()}",
        message=(
            f"Refund for return request #{return_request.id} "
            f"is {refund_status.lower()}. "
            f"Amount: ₹{return_request.refund_amount}."
        ),
        notification_type="refund_updated",
    )

    return return_request
