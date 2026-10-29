
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Locate the Payment Service directory.
SERVICE_DIR = Path(__file__).resolve().parent.parent

# Keep the payment database inside this service.
DATABASE_PATH = SERVICE_DIR / "payments.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# SQLite configuration.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create database sessions.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for payment database models.
Base = declarative_base()


def get_db():
    """Provide a database session to an API request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
