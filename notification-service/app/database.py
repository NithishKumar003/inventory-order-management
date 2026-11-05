from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Find the notification-service folder
SERVICE_DIR = Path(__file__).resolve().parent.parent

# Store the database inside notification-service
DATABASE_PATH = SERVICE_DIR / "notification.db"

# Build the SQLite database URL
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# Connect SQLAlchemy to SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for database models
Base = declarative_base()


# Provide a database session to API endpoints
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
