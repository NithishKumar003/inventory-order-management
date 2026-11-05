from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    order_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    idempotency_key: str = Field(min_length=8, max_length=100)

    # Used only for our simulated payment workflow.
    simulated_outcome: Literal["SUCCESS", "FAILED", "CANCELLED"] = "SUCCESS"


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    user_id: int
    transaction_reference: str
    amount: Decimal
    status: str
    failure_reason: str | None
    created_at: str | None = None


class CheckoutSessionResponse(BaseModel):
    payment_id: int
    session_id: str
    checkout_url: str

class CheckoutSessionCreate(BaseModel):
    order_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    idempotency_key: str = Field(min_length=8, max_length=100)

class RefundCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=250)
    idempotency_key: str = Field(min_length=8, max_length=100)


class RefundResponse(BaseModel):
    id: int
    payment_id: int
    user_id: int
    amount: Decimal
    reason: str
    idempotency_key: str
    status: str
    provider_reference: str | None
    failure_reason: str | None
    created_at: str | None = None
    
class InternalRefundCreate(BaseModel):
    order_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=250)
    idempotency_key: str = Field(min_length=8, max_length=100)