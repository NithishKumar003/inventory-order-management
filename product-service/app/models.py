from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.sql import func

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    brand = Column(String(100), nullable=True, index=True)
    image_url = Column(String(500), nullable=True)
    specifications = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
