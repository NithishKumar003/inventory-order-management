import json
import os
from pathlib import Path

import pika
from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVICE_DIR / ".env")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")

MAIN_QUEUE = "notification_queue"
RETRY_QUEUE = "notification_retry_queue"
DEAD_LETTER_QUEUE = "notification_dead_letter_queue"

RETRY_DELAY_MS = 10000


def get_rabbitmq_connection():
    if not RABBITMQ_USERNAME or not RABBITMQ_PASSWORD:
        raise RuntimeError("RabbitMQ credentials are missing.")

    credentials = pika.PlainCredentials(
        RABBITMQ_USERNAME,
        RABBITMQ_PASSWORD,
    )

    connection_parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=30,
    )

    return pika.BlockingConnection(connection_parameters)


def declare_notification_queue(channel):
    # Failed messages from the main queue go to the retry queue.
    channel.queue_declare(
        queue=RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": RETRY_DELAY_MS,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": MAIN_QUEUE,
        },
    )

    # Main queue sends rejected messages to the retry queue.
    channel.queue_declare(
        queue=MAIN_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": RETRY_QUEUE,
        },
    )

    # Final destination for messages that exceed retry attempts.
    channel.queue_declare(
        queue=DEAD_LETTER_QUEUE,
        durable=True,
    )

    return MAIN_QUEUE


def publish_notification(notification_data: dict):
    connection = get_rabbitmq_connection()

    try:
        channel = connection.channel()
        channel.confirm_delivery()
        declare_notification_queue(channel)

        message = json.dumps(notification_data)

        channel.basic_publish(
            exchange="",
            routing_key=MAIN_QUEUE,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )

        return True

    finally:
        if connection.is_open:
            connection.close()
