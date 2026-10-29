from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def current_utc_time():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Human-readable unique order number
    order_number = Column(String(40), unique=True, nullable=False, index=True)

    # Authenticated customer ID
    user_id = Column(Integer, nullable=False, index=True)

    # Pending, Confirmed, Processing, Shipped, Delivered, Cancelled
    status = Column(String(20), nullable=False, default="Pending")

    # Pricing breakdown
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    shipping_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

    # Idempotency key supplied with the create-order request
    idempotency_key = Column(String(100), nullable=False)

    # Optional delivery information
    shipping_address = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=current_utc_time,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=current_utc_time,
        onupdate=current_utc_time,
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_order_user_idempotency",
        ),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
    )

    product_id = Column(Integer, nullable=False)
    product_name = Column(String(200), nullable=False)

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    line_subtotal = Column(Numeric(12, 2), nullable=False)

    # Pending, Confirmed, Processing, Shipped, Delivered, Cancelled
    status = Column(String(20), nullable=False, default="Pending")

    cancellation_reason = Column(Text, nullable=True)
    cancelled_quantity = Column(Integer, nullable=False, default=0)

    order = relationship("Order", back_populates="items")


class OrderCancellation(Base):
    __tablename__ = "order_cancellations"

    id = Column(Integer, primary_key=True, index=True)
    cancellation_key = Column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )
    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )
    order_item_id = Column(
        Integer,
        ForeignKey("order_items.id"),
        nullable=False,
        index=True,
    )
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=current_utc_time,
    )

class FullOrderCancellation(Base):
    __tablename__ = "full_order_cancellations"

    id = Column(Integer, primary_key=True, index=True)
    cancellation_key = Column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )
    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=current_utc_time,
    )
