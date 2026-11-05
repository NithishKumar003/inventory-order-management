
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReturnCreate(BaseModel):
    order_id: int = Field(gt=0)
    order_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=5, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=100)


class ReturnModeration(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    admin_note: str | None = Field(
        default=None,
        max_length=500,
    )


class ReturnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    order_id: int
    order_item_id: int
    product_id: int
    quantity: int
    reason: str
    status: str
    admin_note: str | None
    idempotency_key: str

    # Refund tracking
    refund_amount: Decimal | None
    payment_refund_id: int | None
    refund_status: str | None
    refund_failure_reason: str | None

    created_at: datetime
    updated_at: datetime
