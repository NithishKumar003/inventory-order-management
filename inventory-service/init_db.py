from app.database import Base, engine
from app.models import (
    AppSetting,
    Inventory,
    StockMovement,
    StockRelease,
    StockReservation,
)

Base.metadata.create_all(bind=engine)

print("Inventory database tables created successfully.")
print("Tables:", list(Base.metadata.tables.keys()))