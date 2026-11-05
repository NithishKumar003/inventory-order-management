from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    product_id: int = Field(gt=0)
    order_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, min_length=3, max_length=120)
    comment: str | None = Field(default=None, min_length=5, max_length=2000)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    product_id: int
    order_id: int
    rating: int
    title: str | None
    comment: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ReviewModeration(BaseModel):
    status: Literal["APPROVED", "REJECTED"]