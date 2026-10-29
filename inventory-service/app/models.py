
from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    quantity_change = Column(Integer, nullable=False)
    reason = Column(String(200), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id = Column(Integer, primary_key=True, index=True)
    reservation_key = Column(String(150), nullable=False, unique=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    released_quantity = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    status = Column(String(20), nullable=False, default="reserved")
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

    __table_args__ = (
        UniqueConstraint(
            "reservation_key",
            "product_id",
            name="uq_reservation_product",
        ),
    )


class StockRelease(Base):
    __tablename__ = "stock_releases"

    id = Column(Integer, primary_key=True, index=True)
    release_key = Column(String(150), nullable=False, unique=True, index=True)
    reservation_key = Column(String(150), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    reason = Column(String(200), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
