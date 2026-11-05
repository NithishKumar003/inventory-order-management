import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.models import Coupon


# Load environment variables from order-service/.env
SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(SERVICE_DIR, ".env"))

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://127.0.0.1:8002",
)

INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL",
    "http://127.0.0.1:8003",
)

INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")


def get_inventory_service_headers() -> dict:
    if not INTERNAL_SERVICE_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Inventory Service credentials are not configured.",
        )

    return {
        "X-Service-Token": INTERNAL_SERVICE_TOKEN,
    }

CART_SERVICE_URL = os.getenv(
    "CART_SERVICE_URL",
    "http://127.0.0.1:8004",
)

TAX_RATE = Decimal(os.getenv("TAX_RATE", "0.18"))
SHIPPING_FEE = Decimal(os.getenv("SHIPPING_FEE", "50.00"))
FREE_SHIPPING_THRESHOLD = Decimal(
    os.getenv("FREE_SHIPPING_THRESHOLD", "1000.00")
)

def get_product(product_id: int) -> dict:
    """Retrieve product details from Product Service."""

    try:
        response = httpx.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=5.0,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Product Service is unavailable.",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} was not found.",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Product Service returned an unexpected response.",
        )

    product = response.json()

    if product.get("is_active") is False:
        raise HTTPException(
            status_code=400,
            detail=f"Product {product_id} is inactive.",
        )

    return product


def get_inventory(product_id: int) -> dict:
    """Retrieve current stock from Inventory Service."""

    try:
        response = httpx.get(
            f"{INVENTORY_SERVICE_URL}/inventory/{product_id}",
            timeout=5.0,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Inventory Service is unavailable.",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=409,
            detail=f"Inventory is not configured for product {product_id}.",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Inventory Service returned an unexpected response.",
        )

    return response.json()


def reserve_inventory(
    reservation_key: str,
    product_id: int,
    quantity: int,
) -> dict:
    """Reserve stock through Inventory Service."""

    try:
        response = httpx.post(
            f"{INVENTORY_SERVICE_URL}/inventory/reservations",
            json={
                "reservation_key": reservation_key,
                "product_id": product_id,
                "quantity": quantity,
            },
            headers=get_inventory_service_headers(),
            timeout=5.0,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Inventory Service is unavailable while reserving stock.",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=409,
            detail=f"Inventory is not configured for product {product_id}.",
        )

    if response.status_code == 409:
        raise HTTPException(
            status_code=409,
            detail=f"Could not reserve stock for product {product_id}.",
        )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail="Inventory Service failed to reserve stock.",
        )

    return response.json()


def release_inventory(
    reservation_key: str,
    reason: str,
) -> None:
    """Release a reservation after an order operation fails."""

    try:
        response = httpx.post(
            f"{INVENTORY_SERVICE_URL}/inventory/reservations/"
            f"{reservation_key}/release",
            json={"reason": reason},
            headers=get_inventory_service_headers(),
            timeout=5.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not contact Inventory Service to release stock.",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Inventory Service failed to release reserved stock.",
        )

def validate_coupon(
    db: Session,
    coupon_code: str | None,
    subtotal: Decimal,
) -> tuple[Coupon | None, Decimal]:
    """Validate a coupon and calculate its discount."""

    if not coupon_code:
        return None, Decimal("0.00")

    coupon = (
        db.query(Coupon)
        .filter(Coupon.code == coupon_code.strip().upper())
        .first()
    )

    if coupon is None:
        raise HTTPException(status_code=400, detail="Invalid coupon code.")

    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="This coupon is inactive.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if coupon.starts_at and now < coupon.starts_at:
        raise HTTPException(status_code=400, detail="This coupon is not active yet.")

    if coupon.expires_at and now > coupon.expires_at:
        raise HTTPException(status_code=400, detail="This coupon has expired.")

    if coupon.usage_limit is not None and coupon.usage_count >= coupon.usage_limit:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached.")

    if subtotal < coupon.minimum_order_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order amount is {coupon.minimum_order_amount}.",
        )

    discount_type = coupon.discount_type.upper()
    discount_value = Decimal(str(coupon.discount_value))

    if discount_type == "PERCENT":
        if not Decimal("0") < discount_value <= Decimal("100"):
            raise HTTPException(status_code=400, detail="Invalid coupon discount.")

        discount = subtotal * discount_value / Decimal("100")

    elif discount_type == "FIXED":
        if discount_value <= Decimal("0"):
            raise HTTPException(status_code=400, detail="Invalid coupon discount.")

        discount = discount_value

    else:
        raise HTTPException(status_code=400, detail="Unsupported coupon discount type.")

    if coupon.maximum_discount_amount is not None:
        discount = min(
            discount,
            Decimal(str(coupon.maximum_discount_amount)),
        )

    discount = min(discount, subtotal).quantize(Decimal("0.01"))

    return coupon, discount

def calculate_order_totals(
    subtotal: Decimal,
    discount_amount: Decimal = Decimal("0.00"),
) -> dict:
    """Calculate tax, shipping, discount, and final total."""

    if subtotal < Decimal("0.00"):
        raise ValueError("Subtotal cannot be negative.")

    subtotal = subtotal.quantize(Decimal("0.01"))
    discount_amount = discount_amount.quantize(Decimal("0.01"))

    if discount_amount < Decimal("0.00") or discount_amount > subtotal:
        raise ValueError("Invalid discount amount.")

    tax_amount = (subtotal * TAX_RATE).quantize(Decimal("0.01"))

    if subtotal >= FREE_SHIPPING_THRESHOLD:
        shipping_amount = Decimal("0.00")
    else:
        shipping_amount = SHIPPING_FEE

    total_amount = (
        subtotal
        + tax_amount
        - discount_amount
        + shipping_amount
    ).quantize(Decimal("0.01"))

    return {
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "shipping_amount": shipping_amount,
        "total_amount": total_amount,
    }

def partially_release_inventory(
    reservation_key: str,
    cancellation_key: str,
    quantity: int,
    reason: str,
) -> dict:
    """Release part of a stock reservation through Inventory Service."""

    try:
        response = httpx.post(
            f"{INVENTORY_SERVICE_URL}/inventory/reservations/"
            f"{reservation_key}/partial-release",
            json={
                "release_key": cancellation_key,
                "quantity": quantity,
                "reason": reason,
            },
            headers=get_inventory_service_headers(),
            timeout=5.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not contact Inventory Service to release stock.",
        ) from exc

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Stock reservation was not found.",
        )

    if response.status_code == 409:
        raise HTTPException(
            status_code=409,
            detail="Inventory Service rejected the stock release request.",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Inventory Service failed to release stock.",
        )

    return response.json()
