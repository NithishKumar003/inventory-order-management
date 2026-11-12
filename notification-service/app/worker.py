import json
import pika

from .database import SessionLocal
from .models import Notification
from .rabbitmq import (
    DEAD_LETTER_QUEUE,
    MAIN_QUEUE,
    RETRY_QUEUE,
    declare_notification_queue,
    get_rabbitmq_connection,
)

MAX_RETRIES = 3


def process_notification(message: dict):
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
            "Notification processed successfully. "
            f"Database ID: {notification.id}"
        )

    finally:
        db.close()


def publish_to_queue(channel, queue_name, message):
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )


def start_worker():
    connection = get_rabbitmq_connection()
    channel = connection.channel()

    channel.confirm_delivery()
    declare_notification_queue(channel)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        try:
            notification_data = json.loads(body)
            process_notification(notification_data)

            ch.basic_ack(
                delivery_tag=method.delivery_tag,
            )

        except Exception as error:
            print("Notification processing failed:", error)

            try:
                notification_data = json.loads(body)

                retry_count = int(
                    notification_data.get("retry_count", 0)
                )

                if retry_count < MAX_RETRIES:
                    notification_data["retry_count"] = retry_count + 1

                    publish_to_queue(
                        ch,
                        RETRY_QUEUE,
                        notification_data,
                    )

                    print(
                        "Notification scheduled for retry:",
                        retry_count + 1,
                    )

                else:
                    publish_to_queue(
                        ch,
                        DEAD_LETTER_QUEUE,
                        notification_data,
                    )

                    print(
                        "Notification moved to dead-letter queue:",
                        notification_data.get("notification_id"),
                    )

                ch.basic_ack(
                    delivery_tag=method.delivery_tag,
                )

            except Exception as retry_error:
                print("Retry handling failed:", retry_error)

                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True,
                )

    channel.basic_consume(
        queue=MAIN_QUEUE,
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
