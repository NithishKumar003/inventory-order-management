
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
        
def migrate_payment_database():
    """Safely add new columns to an existing payment database."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    if "payments" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("payments")
    }

    if "stripe_payment_intent_id" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE payments "
                    "ADD COLUMN stripe_payment_intent_id VARCHAR(255)"
                )
            )