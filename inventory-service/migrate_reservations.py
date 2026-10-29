from sqlalchemy import inspect, text

from app.database import engine


def migrate_reservations():
    inspector = inspect(engine)

    if "stock_reservations" not in inspector.get_table_names():
        print("Stock reservations table does not exist.")
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("stock_reservations")
    }

    if "released_quantity" in columns:
        print("Migration already applied; no changes needed.")
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE stock_reservations
                ADD COLUMN released_quantity INTEGER
                NOT NULL DEFAULT 0
                """
            )
        )

    print("Migration successful: released_quantity added.")


if __name__ == "__main__":
    migrate_reservations()
