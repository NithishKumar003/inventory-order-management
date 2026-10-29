from app.database import Base, engine
from app.models import StockRelease

StockRelease.__table__.create(bind=engine, checkfirst=True)

print("Migration successful: stock_releases table is ready.")
