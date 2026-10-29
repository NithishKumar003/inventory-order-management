from app.database import Base, engine
from app.models import Product

Base.metadata.create_all(bind=engine)

print("Product database tables created successfully.")
print("Table:", list(Base.metadata.tables.keys()))
