import logging
import secrets
from decimal import Decimal, InvalidOperation

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.database import Base, engine, get_db
from app import models
from app.auth import get_current_user
from app.schemas import (
    CancelOrderRequest,
    OrderCreate,
    OrderResponse,
    OrderStatusHistoryResponse,
    OrderStatusUpdate,
    PartialItemCancellationRequest,
    CouponCreate,
    CouponResponse,
    CouponStatusUpdate,
)
from app.services import (
    calculate_order_totals,
    get_product,
    reserve_inventory,
    release_inventory,
    partially_release_inventory,
    validate_coupon,
)
from app.notifications import (
    send_order_notification,
    send_notification,
)

bearer_scheme = HTTPBearer()
logger = logging.getLogger(__name__)
# Create tables that do not already exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Order Management Service",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "order-service",
    }

@app.post(
    "/coupons",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_coupon(
    coupon_data: CouponCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can create coupons.",
        )

    code = coupon_data.code.strip().upper()

    if coupon_data.discount_type == "PERCENT" and coupon_data.discount_value > 100:
        raise HTTPException(
            status_code=400,
            detail="Percentage discount cannot exceed 100.",
        )

    if (
        coupon_data.starts_at is not None
        and coupon_data.expires_at is not None
        and coupon_data.expires_at <= coupon_data.starts_at
    ):
        raise HTTPException(
            status_code=400,
            detail="Coupon expiry must be after its start date.",
        )

    existing_coupon = (
        db.query(models.Coupon)
        .filter(models.Coupon.code == code)
        .first()
    )

    if existing_coupon:
        raise HTTPException(
            status_code=409,
            detail="A coupon with this code already exists.",
        )

    coupon = models.Coupon(
        code=code,
        discount_type=coupon_data.discount_type,
        discount_value=Decimal(str(coupon_data.discount_value)),
        minimum_order_amount=Decimal(
            str(coupon_data.minimum_order_amount)
        ),
        maximum_discount_amount=(
            Decimal(str(coupon_data.maximum_discount_amount))
            if coupon_data.maximum_discount_amount is not None
            else None
        ),
        usage_limit=coupon_data.usage_limit,
        starts_at=coupon_data.starts_at,
        expires_at=coupon_data.expires_at,
        is_active=True,
    )

    db.add(coupon)

    try:
        db.commit()
        db.refresh(coupon)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A coupon with this code already exists.",
        )

    return coupon


@app.get(
    "/coupons",
    response_model=list[CouponResponse],
)
def list_coupons(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can view coupon management.",
        )

    return (
        db.query(models.Coupon)
        .order_by(models.Coupon.id.desc())
        .all()
    )


@app.patch(
    "/coupons/{coupon_id}/status",
    response_model=CouponResponse,
)
def update_coupon_status(
    coupon_id: int,
    status_data: CouponStatusUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update coupons.",
        )

    coupon = (
        db.query(models.Coupon)
        .filter(models.Coupon.id == coupon_id)
        .first()
    )

    if coupon is None:
        raise HTTPException(
            status_code=404,
            detail="Coupon not found.",
        )

    coupon.is_active = status_data.is_active
    db.commit()
    db.refresh(coupon)

    return coupon


@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    user_id = int(user["id"])

    # Return the original order if this request was already processed.
    existing_order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(
            models.Order.user_id == user_id,
            models.Order.idempotency_key == order_data.idempotency_key,
        )
        .first()
    )

    if existing_order is not None:
        existing_items = sorted(
            [
                (item.product_id, item.quantity)
                for item in existing_order.items
            ]
        )

        requested_quantities = {}

        for item in order_data.items:
            requested_quantities[item.product_id] = (
                requested_quantities.get(item.product_id, 0)
                + item.quantity
            )

        requested_items = sorted(requested_quantities.items())

        if (
            existing_order.shipping_address
            != order_data.shipping_address
            or existing_items != requested_items
            or existing_order.coupon_code
            != (
                order_data.coupon_code.strip().upper()
                if order_data.coupon_code
                else None
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This idempotency key was already used "
                    "for a different order request."
                ),
            )

        return existing_order

    # Combine repeated product IDs to avoid reserving the same item twice.
    quantities = {}
    for item in order_data.items:
        quantities[item.product_id] = (
            quantities.get(item.product_id, 0) + item.quantity
        )

    prepared_items = []
    subtotal = Decimal("0.00")

    # Read current product details and calculate the authoritative subtotal.
    for product_id, quantity in quantities.items():
        product = get_product(product_id)

        try:
            unit_price = Decimal(str(product["price"])).quantize(
                Decimal("0.01")
            )
        except (KeyError, InvalidOperation, ValueError, TypeError):
            raise HTTPException(
                status_code=502,
                detail=f"Product {product_id} returned an invalid price.",
            )

        if unit_price <= Decimal("0.00"):
            raise HTTPException(
                status_code=502,
                detail=f"Product {product_id} returned an invalid price.",
            )

        line_subtotal = (unit_price * quantity).quantize(
            Decimal("0.01")
        )
        subtotal += line_subtotal

        prepared_items.append(
            {
                "product_id": product_id,
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "line_subtotal": line_subtotal,
            }
        )

    coupon, discount_amount = validate_coupon(
        db=db,
        coupon_code=order_data.coupon_code,
        subtotal=subtotal,
    )

    totals = calculate_order_totals(
        subtotal,
        discount_amount,
    )

    # Unique order number and reservation keys.
    order_number = f"ORD-{secrets.token_hex(8).upper()}"

    # Reserve each product before persisting the order.
    reserved_keys = []

    try:
        for item in prepared_items:
            reservation_key = (
                f"{order_number}-{item['product_id']}"
            )

            reserve_inventory(
                reservation_key=reservation_key,
                product_id=item["product_id"],
                quantity=item["quantity"],
            )

            reserved_keys.append(reservation_key)

        order = models.Order(
            order_number=order_number,
            user_id=user_id,
            status="Confirmed",
            idempotency_key=order_data.idempotency_key,
            shipping_address=order_data.shipping_address,
            coupon_code=(
                order_data.coupon_code.strip().upper()
                if order_data.coupon_code
                else None
            ),
            **totals,
        )

        for item in prepared_items:
            order.items.append(
                models.OrderItem(
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    line_subtotal=item["line_subtotal"],
                    status="Confirmed",
                )
            )
        
        order.status_history.append(
            models.OrderStatusHistory(
                status="Confirmed",
                note="Your order has been confirmed successfully.",
            )
        )

        db.add(order)

        if coupon is not None:
            coupon.usage_count += 1

        db.commit()
        db.refresh(order)
        
        send_order_notification(
            user_id=user_id,
            order_number=order.order_number,
            total_amount=order.total_amount,
            access_token=credentials.credentials,
        )

        return (
            db.query(models.Order)
            .options(joinedload(models.Order.items))
            .filter(models.Order.id == order.id)
            .first()
        )

    except IntegrityError:
        db.rollback()

        # A concurrent request may have created the same idempotency key.
        existing_order = (
            db.query(models.Order)
            .options(joinedload(models.Order.items))
            .filter(
                models.Order.user_id == user_id,
                models.Order.idempotency_key
                == order_data.idempotency_key,
            )
            .first()
        )

        if existing_order is not None:
            return existing_order

        rollback_failures = []

        for reservation_key in reversed(reserved_keys):
            try:
                release_inventory(
                    reservation_key,
                    "Order database transaction failed",
                )
            except HTTPException:
                rollback_failures.append(reservation_key)

        if rollback_failures:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Order creation failed and some stock reservations could not be released.",
                    "reservation_keys_requiring_reconciliation": rollback_failures,
                },
            )

        raise HTTPException(
            status_code=409,
            detail="The order could not be saved because of a database conflict.",
        )

    except Exception as exc:
        db.rollback()
        rollback_failures = []

        for reservation_key in reversed(reserved_keys):
            try:
                release_inventory(
                    reservation_key,
                    "Order creation failed",
                )
            except HTTPException:
                rollback_failures.append(reservation_key)

        if rollback_failures:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Order creation failed and some stock reservations could not be released.",
                    "reservation_keys_requiring_reconciliation": rollback_failures,
                },
            ) from exc

        if isinstance(exc, HTTPException):
            raise

        raise HTTPException(
            status_code=500,
            detail="Order creation failed.",
        ) from exc


@app.get("/orders", response_model=list[OrderResponse])
def get_order_history(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(user["id"])

    orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(models.Order.user_id == user_id)
        .order_by(models.Order.created_at.desc())
        .all()
    )

    return orders


@app.get(
    "/orders/admin/all",
    response_model=list[OrderResponse],
)
def get_all_orders_for_admin(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required.",
        )

    orders = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.items),
            joinedload(models.Order.status_history),
        )
        .order_by(models.Order.created_at.desc())
        .all()
    )

    return orders


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order_details(
    order_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(user["id"])

    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(
            models.Order.id == order_id,
            models.Order.user_id == user_id,
        )
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    return order

@app.get(
    "/orders/{order_id}/tracking",
    response_model=list[OrderStatusHistoryResponse],
)
def get_order_tracking(
    order_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(user["id"])

    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id)
        .first()
    )

    if order is None or (
        user.get("role") != "admin"
        and order.user_id != user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    return (
        db.query(models.OrderStatusHistory)
        .filter(models.OrderStatusHistory.order_id == order_id)
        .order_by(models.OrderStatusHistory.created_at.asc())
        .all()
    )

@app.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only admins can update order status
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update order status.",
        )

    # Find the order
    order = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.items),
            joinedload(models.Order.status_history),
        )
        .filter(models.Order.id == order_id)
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    # Define allowed status transitions
    allowed_transitions = {
        "Pending": ["Confirmed"],
        "Confirmed": ["Processing"],
        "Processing": ["Shipped"],
        "Shipped": ["Delivered"],
    }

    current_status = order.status
    new_status = status_data.status

    if new_status not in allowed_transitions.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change order status from {current_status} to {new_status}.",
        )

    # Update order status
    order.status = new_status

    # Add the change to tracking history
    order.status_history.append(
        models.OrderStatusHistory(
            status=new_status,
            note=status_data.note,
        )
    )

    db.commit()
    db.refresh(order)

    send_notification(
        user_id=order.user_id,
        title="Order status updated",
        message=(
            f"Your order {order.order_number} "
            f"status has been updated to {new_status}."
        ),
        notification_type="order_status",
        reference=f"order {order.order_number}",
    )

    return order

@app.post(
    "/orders/{order_id}/items/{item_id}/cancel",
    response_model=OrderResponse,
)
def partially_cancel_order_item(
    order_id: int,
    item_id: int,
    cancellation_data: PartialItemCancellationRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(user["id"])

    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(
            models.Order.id == order_id,
            models.Order.user_id == user_id,
        )
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    order_item = next(
        (item for item in order.items if item.id == item_id),
        None,
    )

    if order_item is None:
        raise HTTPException(
            status_code=404,
            detail="Order item not found.",
        )

    # Check whether this cancellation request was already processed.
    existing_cancellation = (
        db.query(models.OrderCancellation)
        .filter(
            models.OrderCancellation.cancellation_key
            == cancellation_data.cancellation_key
        )
        .first()
    )

    if existing_cancellation is not None:
        if (
            existing_cancellation.order_id != order.id
            or existing_cancellation.order_item_id != order_item.id
            or existing_cancellation.quantity
            != cancellation_data.quantity
            or existing_cancellation.reason
            != cancellation_data.reason
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cancellation key was already used "
                    "with different details."
                ),
            )

        return order

    if order.status in ("Cancelled", "Shipped", "Delivered"):
        raise HTTPException(
            status_code=409,
            detail="This order can no longer be cancelled.",
        )

    if order_item.status in ("Cancelled", "Shipped", "Delivered"):
        raise HTTPException(
            status_code=409,
            detail="This order item can no longer be cancelled.",
        )

    remaining_quantity = (
        order_item.quantity - order_item.cancelled_quantity
    )

    if cancellation_data.quantity > remaining_quantity:
        raise HTTPException(
            status_code=409,
            detail="Cancellation quantity exceeds the remaining quantity.",
        )

    reservation_key = f"{order.order_number}-{order_item.product_id}"

    # Restore inventory before recording the cancellation.
    partially_release_inventory(
        reservation_key=reservation_key,
        cancellation_key=cancellation_data.cancellation_key,
        quantity=cancellation_data.quantity,
        reason=cancellation_data.reason,
    )

    try:
        cancellation = models.OrderCancellation(
            cancellation_key=cancellation_data.cancellation_key,
            order_id=order.id,
            order_item_id=order_item.id,
            quantity=cancellation_data.quantity,
            reason=cancellation_data.reason,
        )
        db.add(cancellation)

        order_item.cancelled_quantity += cancellation_data.quantity
        order_item.cancellation_reason = cancellation_data.reason

        if order_item.cancelled_quantity == order_item.quantity:
            order_item.status = "Cancelled"

        if all(
            item.cancelled_quantity == item.quantity
            for item in order.items
        ):
            order.status = "Cancelled"

            order.status_history.append(
                models.OrderStatusHistory(
                    status="Cancelled",
                    note=f"Order fully cancelled: {cancellation_data.reason}",
                )
            )

        db.commit()

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=(
                "Cancellation database update failed. "
                "Inventory may need reconciliation."
            ),
        ) from exc

        if order.status == "Cancelled":
            send_notification(
                user_id=order.user_id,
                title="Order cancelled",
                message=(
                    f"Your order {order.order_number} has been fully cancelled. "
                    f"Reason: {cancellation_data.reason}"
                ),
                notification_type="order_cancelled",
                reference=f"order {order.order_number} cancellation",
            )
        else:
            send_notification(
                user_id=order.user_id,
                title="Order item cancelled",
                message=(
                    f"{cancellation_data.quantity} unit(s) of "
                    f"{order_item.product_name} from order "
                    f"{order.order_number} have been cancelled. "
                    f"Reason: {cancellation_data.reason}"
                ),
                notification_type="order_item_cancelled",
                reference=f"order {order.order_number} item cancellation",
            )

        return (
            db.query(models.Order)
            .options(joinedload(models.Order.items))
            .filter(models.Order.id == order.id)
            .first()
        )

@app.post(
    "/orders/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order(
    order_id: int,
    cancellation_data: CancelOrderRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(user["id"])

    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(
            models.Order.id == order_id,
            models.Order.user_id == user_id,
        )
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    existing_cancellation = (
        db.query(models.FullOrderCancellation)
        .filter(
            models.FullOrderCancellation.cancellation_key
            == cancellation_data.cancellation_key
        )
        .first()
    )

    if existing_cancellation is not None:
        if (
            existing_cancellation.order_id != order.id
            or existing_cancellation.reason != cancellation_data.reason
        ):
            raise HTTPException(
                status_code=409,
                detail="Cancellation key was already used with different details.",
            )

        return order

    if order.status in ("Cancelled", "Shipped", "Delivered"):
        raise HTTPException(
            status_code=409,
            detail="This order can no longer be cancelled.",
        )

    # Release only the quantities that have not already been cancelled.
    try:
        for item in order.items:
            remaining_quantity = item.quantity - item.cancelled_quantity

            if remaining_quantity <= 0:
                continue

            reservation_key = (
                f"{order.order_number}-{item.product_id}"
            )

            release_inventory(
                reservation_key,
                cancellation_data.reason,
            )

        cancellation = models.FullOrderCancellation(
            cancellation_key=cancellation_data.cancellation_key,
            order_id=order.id,
            reason=cancellation_data.reason,
        )
        db.add(cancellation)

        for item in order.items:
            item.cancelled_quantity = item.quantity
            item.cancellation_reason = cancellation_data.reason
            item.status = "Cancelled"

        order.status = "Cancelled"

        order.status_history.append(
            models.OrderStatusHistory(
                status="Cancelled",
                note=f"Order cancelled: {cancellation_data.reason}",
            )
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=(
                "Order cancellation failed. "
                "Inventory may need reconciliation."
            ),
        ) from exc

        send_notification(
            user_id=order.user_id,
            title="Order cancelled",
            message=(
                f"Your order {order.order_number} has been cancelled. "
                f"Reason: {cancellation_data.reason}"
            ),
            notification_type="order_cancelled",
            reference=f"order {order.order_number} cancellation",
        )

        return (
            db.query(models.Order)
            .options(joinedload(models.Order.items))
            .filter(models.Order.id == order.id)
            .first()
        )