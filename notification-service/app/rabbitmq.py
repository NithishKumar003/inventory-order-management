import json
import os
from pathlib import Path

import pika
from dotenv import load_dotenv


# Load Notification Service environment variables
SERVICE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVICE_DIR / ".env")


# RabbitMQ connection settings
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))

RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")


def get_rabbitmq_connection():
    """Create and return an authenticated RabbitMQ connection."""

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
    """Create the notification queue if it does not exist."""

    channel.queue_declare(
        queue="notification_queue",
        durable=True,
    )

    return "notification_queue"


def publish_notification(notification_data: dict):
    """Publish a notification job to RabbitMQ."""

    connection = get_rabbitmq_connection()

    try:
        channel = connection.channel()

        declare_notification_queue(channel)

        message = json.dumps(notification_data)

        channel.basic_publish(
            exchange="",
            routing_key="notification_queue",
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )

        return True

    finally:
        connection.close()
