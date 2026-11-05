
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Numeric,
    UniqueConstraint,
)

from app.database import Base


def current_utc_time():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False, index=True)
    order_id = Column(Integer, nullable=False, index=True)
    order_item_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False)

    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)

    # PENDING, APPROVED, REJECTED, COMPLETED
    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )

    admin_note = Column(Text, nullable=True)
    idempotency_key = Column(String(100), nullable=False)

    # Refund tracking
    refund_amount = Column(Numeric(12, 2), nullable=True)
    payment_refund_id = Column(Integer, nullable=True)
    refund_status = Column(
        String(20),
        nullable=True,
        default="NOT_STARTED",
    )
    refund_failure_reason = Column(Text, nullable=True)

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

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_return_user_idempotency",
        ),
    )
