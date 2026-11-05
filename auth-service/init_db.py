from app.database import Base, engine
from app.models import User, RefreshToken

Base.metadata.create_all(bind=engine)

print("Authentication database tables created successfully.")
print("Tables:", list(Base.metadata.tables.keys())) 