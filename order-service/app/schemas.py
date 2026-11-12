from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


OrderStatus = Literal[
    "Pending",
    "Confirmed",
    "Processing",
    "Shipped",
    "Delivered",
    "Cancelled",
]


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1)
    idempotency_key: str = Field(min_length=8, max_length=100)
    shipping_address: str = Field(min_length=5, max_length=500)
    coupon_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=40,
    )

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    line_subtotal: float
    status: str
    cancelled_quantity: int
    cancellation_reason: str | None

class OrderStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    note: str | None
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    user_id: int
    status: OrderStatus
    subtotal: float
    tax_amount: float
    discount_amount: float
    coupon_code: str | None
    shipping_amount: float
    total_amount: float
    shipping_address: str | None
    items: list[OrderItemResponse]
    status_history: list[OrderStatusHistoryResponse] = []


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = Field(
        default=None,
        min_length=3,
        max_length=300,
    )

class CancelOrderRequest(BaseModel):
    cancellation_key: str = Field(min_length=8, max_length=150)
    reason: str = Field(min_length=3, max_length=300)

class PartialItemCancellationRequest(BaseModel):
    cancellation_key: str = Field(min_length=8, max_length=150)
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=300)

class CouponValidateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=40)
    subtotal: float = Field(gt=0)

class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=40)
    discount_type: Literal["PERCENT", "FIXED"]
    discount_value: float = Field(gt=0)
    minimum_order_amount: float = Field(default=0, ge=0)
    maximum_discount_amount: float | None = Field(default=None, gt=0)
    usage_limit: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: str
    discount_value: float
    minimum_order_amount: float
    maximum_discount_amount: float | None
    usage_limit: int | None
    usage_count: int
    starts_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class CouponStatusUpdate(BaseModel):
    is_active: bool