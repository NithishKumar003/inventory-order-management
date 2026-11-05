import os
from pathlib import Path

from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(SERVICE_DIR / ".env")

AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL",
    "http://127.0.0.1:8001",
).rstrip("/")

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://127.0.0.1:8002",
).rstrip("/")

INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL",
    "http://127.0.0.1:8003",
).rstrip("/")

ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL",
    "http://127.0.0.1:8005",
).rstrip("/")

PAYMENT_SERVICE_URL = os.getenv(
    "PAYMENT_SERVICE_URL",
    "http://127.0.0.1:8006",
).rstrip("/")

RETURN_SERVICE_URL = os.getenv(
    "RETURN_SERVICE_URL",
    "http://127.0.0.1:8009",
).rstrip("/")

ANALYTICS_SERVICE_NAME = "analytics-service"
ANALYTICS_SERVICE_VERSION = "1.0.0"
