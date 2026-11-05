from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker


SERVICE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = SERVICE_DIR / "returns.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def migrate_return_database():
    """Add refund tracking columns without deleting existing records."""

    migrations = {
        "refund_amount": "NUMERIC(12, 2)",
        "payment_refund_id": "INTEGER",
        "refund_status": "VARCHAR(20) DEFAULT 'NOT_STARTED'",
        "refund_failure_reason": "TEXT",
    }

    with engine.begin() as connection:
        existing_columns = {
            column["name"]
            for column in connection.execute(
                text("PRAGMA table_info(return_requests)")
            ).mappings()
        }

        # A fresh database may not have the table yet.
        if not existing_columns:
            return

        for column_name, column_definition in migrations.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE return_requests "
                        f"ADD COLUMN {column_name} {column_definition}"
                    )
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
