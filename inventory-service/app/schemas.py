from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class InventoryCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=0)

class InventoryUpdate(BaseModel):
    quantity: int = Field(ge=0)

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    updated_at: datetime | None

    model_config = ConfigDict(form_attributes=True)

class StockMovementCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity_change: int
    reason: str = Field(min_length=3, max_length=200)

    @field_validator("quantity_change")
    @classmethod
    def quantity_change_must_not_be_zero(cls, value):
        if value == 0:
            raise ValueError("Quantity change cannot be zero.")
        return value

class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    quantity_change: int
    reason: str
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class StockReservationCreate(BaseModel):
    reservation_key: str = Field(min_length=8, max_length=150)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class StockReservationResponse(BaseModel):
    id: int
    reservation_key: str
    product_id: int
    quantity: int
    released_quantity: int
    status: str
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class StockReservationRelease(BaseModel):
    reason: str = Field(min_length=3, max_length=200)

class StockReservationPartialRelease(BaseModel):
    release_key: str = Field(min_length=8, max_length=150)
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=200)
