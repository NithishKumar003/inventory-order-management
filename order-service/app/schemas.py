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


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    user_id: int
    status: OrderStatus
    subtotal: float
    tax_amount: float
    discount_amount: float
    shipping_amount: float
    total_amount: float
    shipping_address: str | None
    items: list[OrderItemResponse]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class CancelOrderRequest(BaseModel):
    cancellation_key: str = Field(min_length=8, max_length=150)
    reason: str = Field(min_length=3, max_length=300)

class PartialItemCancellationRequest(BaseModel):
    cancellation_key: str = Field(min_length=8, max_length=150)
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=300)
