import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from decimal import Decimal, InvalidOperation


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

def calculate_order_totals(subtotal: Decimal) -> dict:
    """Calculate tax, shipping, discount, and final total."""

    if subtotal < Decimal("0.00"):
        raise ValueError("Subtotal cannot be negative.")

    tax_amount = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
    discount_amount = Decimal("0.00")

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
        "subtotal": subtotal.quantize(Decimal("0.01")),
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
