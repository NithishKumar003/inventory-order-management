import secrets
from decimal import Decimal, InvalidOperation

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import Base, engine, get_db
from app import models
from app.auth import get_current_user
from app.schemas import (
    CancelOrderRequest,
    OrderCreate,
    OrderResponse,
    PartialItemCancellationRequest,
)
from app.services import (
    calculate_order_totals,
    get_product,
    reserve_inventory,
    release_inventory,
    partially_release_inventory,
)

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
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
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

    totals = calculate_order_totals(subtotal)

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

        db.add(order)
        db.commit()
        db.refresh(order)

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

    return (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(models.Order.id == order.id)
        .first()
    )
