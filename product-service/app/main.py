
import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Product
from app.schemas import ProductCreate, ProductResponse, ProductUpdate


INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL",
    "http://127.0.0.1:8003",
).rstrip("/")

app = FastAPI(
    title="Inventory Management - Product Service",
    description="Manages products and product catalogue filters.",
    version="1.1.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_stock_quantity(product_id: int) -> int:
    """Get stock quantity from the Inventory Service."""
    try:
        response = httpx.get(
            f"{INVENTORY_SERVICE_URL}/inventory/{product_id}",
            timeout=5.0,
        )

        # A product without an inventory record is treated as out of stock.
        if response.status_code == 404:
            return 0

        response.raise_for_status()
        inventory_data = response.json()
        quantity = inventory_data.get("quantity")

        if quantity is None:
            raise HTTPException(
                status_code=502,
                detail="Inventory Service returned no stock quantity.",
            )

        return int(quantity)

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Inventory Service timed out.",
        )
    except (httpx.HTTPError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve stock from Inventory Service.",
        )


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "product-service",
    }


@app.get("/products", response_model=list[ProductResponse])
def list_products(
    search: str | None = Query(default=None, min_length=1),
    category: str | None = Query(default=None, min_length=1),
    brand: str | None = Query(default=None, min_length=1),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    in_stock: bool | None = Query(
        default=None,
        description="True for available products; false for out-of-stock products.",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="asc"),
    db: Session = Depends(get_db),
):
    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise HTTPException(
            status_code=400,
            detail="Minimum price cannot exceed maximum price.",
        )

    allowed_sort_fields = {
        "id": Product.id,
        "name": Product.name,
        "price": Product.price,
        "category": Product.category,
        "brand": Product.brand,
    }

    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort field. Use id, name, price, category, or brand.",
        )

    if sort_order not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="Invalid sort order. Use asc or desc.",
        )

    query = db.query(Product).filter(Product.is_active.is_(True))

    if search:
        search_text = f"%{search.strip()}%"
        query = query.filter(
            Product.name.ilike(search_text)
            | Product.sku.ilike(search_text)
        )

    if category:
        query = query.filter(Product.category.ilike(category.strip()))

    if brand:
        query = query.filter(Product.brand.ilike(brand.strip()))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    sort_column = allowed_sort_fields[sort_by]
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply database pagination directly when stock filtering is not requested.
    if in_stock is None:
        return query.offset(skip).limit(limit).all()

    # Stock lives in another service, so check matching products before
    # applying pagination. This ensures the requested page contains matches.
    products = query.all()
    matching_products = []

    for product in products:
        quantity = get_stock_quantity(product.id)

        if in_stock and quantity > 0:
            matching_products.append(product)
        elif not in_stock and quantity <= 0:
            matching_products.append(product)

    return matching_products[skip : skip + limit]


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return product


@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
):
    existing_product = (
        db.query(Product)
        .filter(Product.sku == product_data.sku)
        .first()
    )

    if existing_product:
        raise HTTPException(
            status_code=409,
            detail="A product with this SKU already exists.",
        )

    new_product = Product(
        name=product_data.name,
        description=product_data.description,
        sku=product_data.sku,
        price=product_data.price,
        category=product_data.category,
        brand=product_data.brand,
        image_url=product_data.image_url,
        specifications=product_data.specifications,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    update_data = product_data.model_dump(exclude_unset=True)

    if "sku" in update_data:
        existing_product = (
            db.query(Product)
            .filter(
                Product.sku == update_data["sku"],
                Product.id != product_id,
            )
            .first()
        )

        if existing_product:
            raise HTTPException(
                status_code=409,
                detail="A product with this SKU already exists.",
            )

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    product.is_active = False
    db.commit()

    return {
        "message": "Product deactivated successfully.",
        "product_id": product_id,
    }
