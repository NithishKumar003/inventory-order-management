import os
from statistics import mean

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Review
from app.schemas import ReviewCreate, ReviewModeration, ReviewResponse
from app.auth import get_current_user

SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://127.0.0.1:8002",
).rstrip("/")

ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL",
    "http://127.0.0.1:8005",
).rstrip("/")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Review and Rating Service",
    description="Handles verified product reviews and ratings.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "review-service",
    }


def verify_product(product_id: int):
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
            detail="Product not found.",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Could not verify product with Product Service.",
        )

    return response.json()


def verify_delivered_purchase(
    order_id: int,
    product_id: int,
    user_id: int,
    authorization: str | None,
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization token is required.",
        )

    try:
        response = httpx.get(
            f"{ORDER_SERVICE_URL}/orders/{order_id}",
            headers={"Authorization": authorization},
            timeout=5.0,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Order Service is unavailable.",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Order not found for this customer.",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Could not verify order with Order Service.",
        )

    order = response.json()

    if int(order["user_id"]) != user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot review another customer's order.",
        )

    if order["status"] != "Delivered":
        raise HTTPException(
            status_code=400,
            detail="You can review a product only after its order is delivered.",
        )

    matching_item = next(
        (
            item
            for item in order.get("items", [])
            if int(item["product_id"]) == product_id
            and int(item["quantity"]) > int(item.get("cancelled_quantity", 0))
        ),
        None,
    )

    if matching_item is None:
        raise HTTPException(
            status_code=400,
            detail="This product is not included in the delivered order.",
        )


@app.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    review_data: ReviewCreate,
    user: dict = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = int(user["id"])

    verify_product(review_data.product_id)

    verify_delivered_purchase(
        order_id=review_data.order_id,
        product_id=review_data.product_id,
        user_id=user_id,
        authorization=authorization,
    )

    existing_review = (
        db.query(Review)
        .filter(
            Review.user_id == user_id,
            Review.product_id == review_data.product_id,
        )
        .first()
    )

    if existing_review:
        raise HTTPException(
            status_code=409,
            detail="You have already reviewed this product.",
        )

    review = Review(
        user_id=user_id,
        product_id=review_data.product_id,
        order_id=review_data.order_id,
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment,
        status="PENDING",
    )

    db.add(review)

    try:
        db.commit()
        db.refresh(review)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Review could not be saved. You may already have reviewed this product.",
        )

    return review


@app.get(
    "/products/{product_id}/reviews",
    response_model=list[ReviewResponse],
)
def get_product_reviews(
    product_id: int,
    db: Session = Depends(get_db),
):
    verify_product(product_id)

    return (
        db.query(Review)
        .filter(
            Review.product_id == product_id,
            Review.status == "APPROVED",
        )
        .order_by(Review.created_at.desc())
        .all()
    )


@app.get("/products/{product_id}/rating-summary")
def get_rating_summary(
    product_id: int,
    db: Session = Depends(get_db),
):
    verify_product(product_id)

    ratings = (
        db.query(Review.rating)
        .filter(
            Review.product_id == product_id,
            Review.status == "APPROVED",
        )
        .all()
    )

    rating_values = [item[0] for item in ratings]

    return {
        "product_id": product_id,
        "average_rating": round(mean(rating_values), 2) if rating_values else None,
        "total_reviews": len(rating_values),
    }


@app.get(
    "/reviews/me",
    response_model=list[ReviewResponse],
)
def get_my_reviews(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Review)
        .filter(Review.user_id == int(user["id"]))
        .order_by(Review.created_at.desc())
        .all()
    )


@app.get(
    "/admin/reviews",
    response_model=list[ReviewResponse],
)
def list_reviews_for_moderation(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can manage reviews.",
        )

    return (
        db.query(Review)
        .order_by(Review.created_at.desc())
        .all()
    )


@app.patch(
    "/admin/reviews/{review_id}/moderation",
    response_model=ReviewResponse,
)
def moderate_review(
    review_id: int,
    moderation: ReviewModeration,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can moderate reviews.",
        )

    review = (
        db.query(Review)
        .filter(Review.id == review_id)
        .first()
    )

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found.",
        )

    review.status = moderation.status
    db.commit()
    db.refresh(review)

    return review