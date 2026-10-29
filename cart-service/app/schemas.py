
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0, le=1000)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=1000)


class CartItemResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WishlistItemCreate(BaseModel):
    product_id: int = Field(gt=0)


class WishlistItemResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CartLineResponse(BaseModel):
    product_id: int
    name: str
    sku: str
    quantity: int
    unit_price: float
    line_total: float
    available_quantity: int


class CartResponse(BaseModel):
    items: list[CartLineResponse]
    item_count: int
    total_amount: float


class CartValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
