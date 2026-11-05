
import json

from .database import SessionLocal
from .models import Notification
from .rabbitmq import (
    get_rabbitmq_connection,
    declare_notification_queue,
)


def process_notification(message: dict):
    """Process an existing notification using its database ID."""

    db = SessionLocal()

    try:
        notification_id = message["notification_id"]

        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )

        if notification is None:
            raise ValueError(
                f"Notification {notification_id} was not found."
            )

        print(
            f"Notification processed successfully. "
            f"Database ID: {notification.id}"
        )

    finally:
        db.close()


def start_worker():
    """Listen continuously for notification messages."""

    connection = get_rabbitmq_connection()
    channel = connection.channel()

    declare_notification_queue(channel)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        try:
            notification_data = json.loads(body)

            process_notification(notification_data)

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as error:
            print("Notification processing failed:", error)

            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )

    channel.basic_consume(
        queue="notification_queue",
        on_message_callback=callback,
    )

    print("Notification worker started. Waiting for messages...")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping notification worker...")
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    start_worker()
