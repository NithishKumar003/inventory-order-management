
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.database import Base, SessionLocal, engine
from app.models import CartItem, WishlistItem
from app.schemas import (
    CartItemCreate,
    CartItemUpdate,
    CartLineResponse,
    CartResponse,
    CartValidationResponse,
    WishlistItemCreate,
    WishlistItemResponse,
)

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVICE_DIR / ".env")

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL", "http://127.0.0.1:8002"
).rstrip("/")

INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL", "http://127.0.0.1:8003"
).rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Inventory Management - Cart and Wishlist Service",
    description="Manages authenticated customer carts and wishlists.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def fetch_product(product_id: int) -> dict:
    """Retrieve an active product from the Product Service."""
    try:
        response = httpx.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=5.0,
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Product does not exist or is inactive.",
            )

        response.raise_for_status()
        product = response.json()

        if not product.get("is_active", False):
            raise HTTPException(
                status_code=409,
                detail="Product is inactive.",
            )

        return product

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Product Service timed out.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Product Service is unavailable.",
        )


def fetch_stock(product_id: int) -> int:
    """Retrieve current inventory quantity."""
    try:
        response = httpx.get(
            f"{INVENTORY_SERVICE_URL}/inventory/{product_id}",
            timeout=5.0,
        )

        if response.status_code == 404:
            return 0

        response.raise_for_status()
        data = response.json()

        if data.get("quantity") is None:
            raise HTTPException(
                status_code=502,
                detail="Inventory Service returned no quantity.",
            )

        quantity = int(data["quantity"])

        if quantity < 0:
            raise HTTPException(
                status_code=502,
                detail="Inventory Service returned invalid stock.",
            )

        return quantity

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Inventory Service timed out.",
        )
    except (httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve inventory.",
        )


def validate_product_and_stock(
    product_id: int,
    requested_quantity: int = 1,
) -> tuple[dict, int]:
    product = fetch_product(product_id)
    stock = fetch_stock(product_id)

    if stock < requested_quantity:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Insufficient stock for product {product_id}. "
                f"Available: {stock}; requested: {requested_quantity}."
            ),
        )

    return product, stock


def get_cart_response(db: Session, user_id: int) -> CartResponse:
    cart_items = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.id.asc())
        .all()
    )

    lines = []
    total_amount = 0.0
    item_count = 0

    for item in cart_items:
        product = fetch_product(item.product_id)
        available_quantity = fetch_stock(item.product_id)
        unit_price = float(product["price"])
        line_total = round(unit_price * item.quantity, 2)

        lines.append(
            CartLineResponse(
                product_id=item.product_id,
                name=product["name"],
                sku=product["sku"],
                quantity=item.quantity,
                unit_price=unit_price,
                line_total=line_total,
                available_quantity=available_quantity,
            )
        )

        total_amount += line_total
        item_count += item.quantity

    return CartResponse(
        items=lines,
        item_count=item_count,
        total_amount=round(total_amount, 2),
    )


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "cart-service",
    }


@app.get("/cart", response_model=CartResponse)
def get_cart(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_cart_response(db, user_id)


@app.post("/cart/items", status_code=status.HTTP_201_CREATED)
def add_cart_item(
    item_data: CartItemCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Validate stock before adding or increasing quantity.
    existing = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.product_id == item_data.product_id,
        )
        .first()
    )

    new_quantity = item_data.quantity
    if existing:
        new_quantity += existing.quantity

    validate_product_and_stock(item_data.product_id, new_quantity)

    if existing:
        existing.quantity = new_quantity
        db.commit()
        db.refresh(existing)
        return {
            "message": "Cart quantity increased successfully.",
            "product_id": existing.product_id,
            "quantity": existing.quantity,
        }

    item = CartItem(
        user_id=user_id,
        product_id=item_data.product_id,
        quantity=item_data.quantity,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Product added to cart successfully.",
        "product_id": item.product_id,
        "quantity": item.quantity,
    }


@app.put("/cart/items/{product_id}")
def update_cart_item(
    product_id: int,
    item_data: CartItemUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Product is not in your cart.",
        )

    validate_product_and_stock(product_id, item_data.quantity)

    item.quantity = item_data.quantity
    db.commit()

    return {
        "message": "Cart quantity updated successfully.",
        "product_id": product_id,
        "quantity": item.quantity,
    }


@app.delete("/cart/items/{product_id}")
def remove_cart_item(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Product is not in your cart.",
        )

    db.delete(item)
    db.commit()

    return {"message": "Product removed from cart."}


@app.delete("/cart")
def clear_cart(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    db.query(CartItem).filter(
        CartItem.user_id == user_id
    ).delete(synchronize_session=False)

    db.commit()
    return {"message": "Cart cleared successfully."}


@app.post("/cart/validate", response_model=CartValidationResponse)
def validate_cart(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id)
        .all()
    )

    errors = []

    if not items:
        errors.append("Your cart is empty.")

    for item in items:
        try:
            product = fetch_product(item.product_id)
            stock = fetch_stock(item.product_id)

            if stock < item.quantity:
                errors.append(
                    f"{product['name']}: requested {item.quantity}, "
                    f"available {stock}."
                )

        except HTTPException as exc:
            if exc.status_code in (404, 409):
                errors.append(
                    f"Product {item.product_id} is unavailable."
                )
            else:
                raise

    return CartValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
    )


@app.get(
    "/wishlist",
    response_model=list[WishlistItemResponse],
)
def get_wishlist(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return (
        db.query(WishlistItem)
        .filter(WishlistItem.user_id == user_id)
        .order_by(WishlistItem.id.asc())
        .all()
    )


@app.post(
    "/wishlist/items",
    response_model=WishlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_wishlist_item(
    item_data: WishlistItemCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    fetch_product(item_data.product_id)

    existing = (
        db.query(WishlistItem)
        .filter(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == item_data.product_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Product is already in your wishlist.",
        )

    item = WishlistItem(
        user_id=user_id,
        product_id=item_data.product_id,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@app.delete("/wishlist/items/{product_id}")
def remove_wishlist_item(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = (
        db.query(WishlistItem)
        .filter(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Product is not in your wishlist.",
        )

    db.delete(item)
    db.commit()

    return {"message": "Product removed from wishlist."}


@app.post("/wishlist/items/{product_id}/move-to-cart")
def move_wishlist_item_to_cart(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    saved_item = (
        db.query(WishlistItem)
        .filter(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
        )
        .first()
    )

    if saved_item is None:
        raise HTTPException(
            status_code=404,
            detail="Product is not in your wishlist.",
        )

    existing_cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
        )
        .first()
    )

    quantity = 1
    if existing_cart_item:
        quantity += existing_cart_item.quantity

    validate_product_and_stock(product_id, quantity)

    if existing_cart_item:
        existing_cart_item.quantity = quantity
    else:
        db.add(
            CartItem(
                user_id=user_id,
                product_id=product_id,
                quantity=1,
            )
        )

    db.delete(saved_item)
    db.commit()

    return {
        "message": "Product moved from wishlist to cart.",
        "product_id": product_id,
        "quantity": quantity,
    }
