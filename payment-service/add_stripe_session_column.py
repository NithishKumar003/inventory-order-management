import sqlite3
from pathlib import Path

database_path = Path(__file__).resolve().parent / "payments.db"

connection = sqlite3.connect(database_path)

try:
    columns = [
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(payments)"
        ).fetchall()
    ]

    if "stripe_session_id" not in columns:
        connection.execute(
            "ALTER TABLE payments ADD COLUMN stripe_session_id VARCHAR(255)"
        )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        uq_payments_stripe_session_id
        ON payments (stripe_session_id)
        """
    )

    connection.commit()
    print("Stripe session column migration completed.")
finally:
    connection.close()
