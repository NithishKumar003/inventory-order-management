from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    sku: str = Field(min_length=2, max_length=50)
    price: float = Field(gt=0)
    category: str = Field(min_length=2, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    specifications: dict[str, Any] | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    sku: str | None = Field(default=None, min_length=2, max_length=50)
    price: float | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=2, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    specifications: dict[str, Any] | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sku: str
    price: float
    category: str
    brand: str | None
    image_url: str | None
    specifications: dict[str, Any] | None
    is_active: bool
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
