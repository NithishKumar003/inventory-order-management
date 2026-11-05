
import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RefundStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_payment_user_idempotency",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    transaction_reference = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    stripe_session_id = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    # Stripe PaymentIntent used for refunds.
    stripe_payment_intent_id = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    idempotency_key = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)

    status = Column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    failure_reason = Column(String(250), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Refund(Base):
    __tablename__ = "refunds"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_refund_user_idempotency",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    payment_id = Column(
        Integer,
        ForeignKey("payments.id"),
        nullable=False,
        index=True,
    )

    user_id = Column(Integer, nullable=False, index=True)

    amount = Column(Numeric(12, 2), nullable=False)

    reason = Column(String(250), nullable=False)

    idempotency_key = Column(String(100), nullable=False)

    status = Column(
        Enum(RefundStatus),
        default=RefundStatus.PENDING,
        nullable=False,
    )

    provider_reference = Column(String(255), nullable=True)

    failure_reason = Column(String(250), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
