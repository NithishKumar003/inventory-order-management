import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

# Add the API Gateway folder to Python's import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


@pytest.fixture
def gateway(monkeypatch):
    """Test the gateway with fake downstream services."""
    captured = {}

    class FakeRedis:
        def __init__(self):
            self.counts = {}
            self.cache = {}

        async def eval(self, script, numkeys, key, window):
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        async def get(self, key):
            return self.cache.get(key)

        async def setex(self, key, ttl, value):
            self.cache[key] = value

        async def scan_iter(self, match=None):
            for key in list(self.cache.keys()):
                if match is None or key.startswith("product_cache:"):
                    yield key

        async def delete(self, key):
            self.cache.pop(key, None)

    service_urls = {
        "AUTH_SERVICE_URL": "http://auth.test",
        "PRODUCT_SERVICE_URL": "http://product.test",
        "INVENTORY_SERVICE_URL": "http://inventory.test",
        "CART_SERVICE_URL": "http://cart.test",
        "ORDER_SERVICE_URL": "http://order.test",
        "PAYMENT_SERVICE_URL": "http://payment.test",
        "NOTIFICATION_SERVICE_URL": "http://notification.test",
        "REVIEW_SERVICE_URL": "http://review.test",
        "RETURN_SERVICE_URL": "http://return.test",
    }

    for setting, url in service_urls.items():
        monkeypatch.setattr(main, setting, url)

    def handler(request):
        captured["method"] = request.method
        captured["calls"] = captured.get("calls", 0) + 1
        captured["url"] = str(request.url)
        captured["path"] = request.url.path
        captured["query"] = list(request.url.params.multi_items())
        captured["body"] = request.content
        captured["headers"] = dict(request.headers)

        return httpx.Response(
            200,
            json={"message": "downstream response"},
            headers={"X-Downstream": "received"},
        )

    transport = httpx.MockTransport(handler)
    upstream_client = httpx.AsyncClient(transport=transport)

    client = TestClient(main.app)
    main.app.state.http_client = upstream_client
    main.app.state.redis = FakeRedis()

    yield client, captured

    client.close()
    asyncio.run(upstream_client.aclose())


def test_gateway_health(gateway):
    client, _ = gateway

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "api-gateway",
    }


@pytest.mark.parametrize(
    ("gateway_path", "expected_url"),
    [
        ("/auth/health", "http://auth.test/health"),
        ("/products", "http://product.test/products"),
        ("/products/12", "http://product.test/products/12"),
        ("/inventory", "http://inventory.test/inventory/"),
        ("/inventory/12", "http://inventory.test/inventory/12"),
        ("/cart", "http://cart.test/cart"),
        ("/cart/health", "http://cart.test/health"),
        ("/wishlist", "http://cart.test/wishlist"),
        ("/orders", "http://order.test/orders"),
        ("/orders/health", "http://order.test/health"),
        ("/payments", "http://payment.test/payments"),
        ("/payments/health", "http://payment.test/health"),
        (
            "/notifications/",
            "http://notification.test/notifications/",
        ),
        (
            "/notifications/health",
            "http://notification.test/health",
        ),
        ("/reviews", "http://review.test/reviews"),
        ("/reviews/me", "http://review.test/reviews/me"),
        (
            "/reviews/products/5/reviews",
            "http://review.test/products/5/reviews",
        ),
        (
            "/reviews/products/5/rating-summary",
            "http://review.test/products/5/rating-summary",
        ),
        (
            "/reviews/admin",
            "http://review.test/admin/reviews",
        ),
        (
            "/reviews/admin/1/moderation",
            "http://review.test/admin/reviews/1/moderation",
        ),
        ("/reviews/health", "http://review.test/health"),
        ("/returns", "http://return.test/returns"),
        ("/returns/me", "http://return.test/returns/me"),
        ("/returns/admin", "http://return.test/returns/admin"),
        (
            "/returns/admin/1/moderation",
            "http://return.test/returns/admin/1/moderation",
        ),
        ("/returns/health", "http://return.test/health"),
    ],
)
def test_service_routing(gateway, gateway_path, expected_url):
    client, captured = gateway

    response = client.get(gateway_path)

    assert response.status_code == 200
    assert captured["url"] == expected_url


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/products"),
        ("POST", "/products"),
        ("PUT", "/products/12"),
        ("PATCH", "/products/12"),
        ("DELETE", "/products/12"),
        ("POST", "/auth/register"),
        ("POST", "/auth/login"),
        ("POST", "/inventory/movements"),
        ("POST", "/cart"),
        ("DELETE", "/cart"),
        ("POST", "/orders"),
        ("POST", "/payments/checkout"),
        ("GET", "/notifications/"),
        ("POST", "/notifications/"),
        ("PATCH", "/notifications/1/read"),
        ("POST", "/reviews"),
        ("GET", "/reviews/me"),
        ("PATCH", "/reviews/admin/1/moderation"),
        ("POST", "/returns"),
        ("GET", "/returns/me"),
        ("PATCH", "/returns/admin/1/moderation"),
    ],
)
def test_http_method_forwarding(gateway, method, path):
    client, captured = gateway

    response = client.request(method, path)

    assert response.status_code == 200
    assert captured["method"] == method


def test_query_parameters_are_forwarded(gateway):
    client, captured = gateway

    response = client.get(
        "/products",
        params=[
            ("category", "electronics"),
            ("brand", "Example"),
            ("brand", "Another"),
        ],
    )

    assert response.status_code == 200
    assert captured["query"] == [
        ("category", "electronics"),
        ("brand", "Example"),
        ("brand", "Another"),
    ]


def test_review_query_parameters_are_forwarded(gateway):
    client, captured = gateway

    response = client.get(
        "/reviews/products/5/reviews",
        params=[("rating", 5)],
    )

    assert response.status_code == 200
    assert captured["url"] == (
        "http://review.test/products/5/reviews?rating=5"
    )


def test_return_query_parameters_are_forwarded(gateway):
    client, captured = gateway

    response = client.get(
        "/returns/me",
        params=[("status", "APPROVED")],
    )

    assert response.status_code == 200
    assert captured["url"] == (
        "http://return.test/returns/me?status=APPROVED"
    )


def test_json_body_is_forwarded(gateway):
    client, captured = gateway

    payload = {
        "name": "Test Product",
        "sku": "TEST-001",
        "price": 500,
    }

    response = client.post("/products", json=payload)

    assert response.status_code == 200
    assert json.loads(captured["body"]) == payload


def test_review_json_body_is_forwarded(gateway):
    client, captured = gateway

    payload = {
        "product_id": 5,
        "order_id": 1,
        "rating": 5,
        "title": "Excellent",
        "comment": "Works perfectly",
    }

    response = client.post("/reviews", json=payload)

    assert response.status_code == 200
    assert json.loads(captured["body"]) == payload


def test_return_json_body_is_forwarded(gateway):
    client, captured = gateway

    payload = {
        "order_id": 1,
        "order_item_id": 10,
        "quantity": 1,
        "reason": "Product is damaged",
        "idempotency_key": "return-test-001",
    }

    response = client.post("/returns", json=payload)

    assert response.status_code == 200
    assert json.loads(captured["body"]) == payload


def test_authorization_header_is_forwarded(gateway):
    client, captured = gateway

    response = client.get(
        "/orders",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert captured["headers"]["authorization"] == "Bearer test-token"


def test_review_authorization_header_is_forwarded(gateway):
    client, captured = gateway

    response = client.post(
        "/reviews",
        headers={"Authorization": "Bearer review-test-token"},
        json={"product_id": 5, "order_id": 1, "rating": 5},
    )

    assert response.status_code == 200
    assert (
        captured["headers"]["authorization"]
        == "Bearer review-test-token"
    )


def test_return_authorization_header_is_forwarded(gateway):
    client, captured = gateway

    response = client.post(
        "/returns",
        headers={"Authorization": "Bearer return-test-token"},
        json={
            "order_id": 1,
            "order_item_id": 10,
            "quantity": 1,
            "reason": "Product is damaged",
            "idempotency_key": "return-test-001",
        },
    )

    assert response.status_code == 200
    assert (
        captured["headers"]["authorization"]
        == "Bearer return-test-token"
    )


def test_downstream_response_is_preserved(gateway):
    client, _ = gateway

    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == {"message": "downstream response"}
    assert response.headers["x-downstream"] == "received"


@pytest.mark.parametrize(
    ("path", "service_setting", "error_message"),
    [
        (
            "/auth/login",
            "AUTH_SERVICE_URL",
            "Authentication service is unavailable.",
        ),
        (
            "/products",
            "PRODUCT_SERVICE_URL",
            "Product service is unavailable.",
        ),
        (
            "/inventory/1",
            "INVENTORY_SERVICE_URL",
            "Inventory service is unavailable.",
        ),
        (
            "/cart",
            "CART_SERVICE_URL",
            "Cart service is unavailable.",
        ),
        (
            "/orders",
            "ORDER_SERVICE_URL",
            "Order service is unavailable.",
        ),
        (
            "/payments/checkout",
            "PAYMENT_SERVICE_URL",
            "Payment service is unavailable.",
        ),
        (
            "/notifications/",
            "NOTIFICATION_SERVICE_URL",
            "Notification service is unavailable.",
        ),
        (
            "/reviews",
            "REVIEW_SERVICE_URL",
            "Review service is unavailable.",
        ),
        (
            "/returns",
            "RETURN_SERVICE_URL",
            "Return service is unavailable.",
        ),
    ],
)
def test_service_unavailable_returns_503(
    gateway, monkeypatch, path, service_setting, error_message
):
    client, _ = gateway

    async def fail_request(*args, **kwargs):
        raise httpx.ConnectError("Test connection failure")

    monkeypatch.setattr(
        main.app.state.http_client,
        "request",
        fail_request,
    )

    response = client.get(path)

    assert response.status_code == 503
    assert response.json() == {"detail": error_message}


def test_downstream_error_status_is_preserved(gateway, monkeypatch):
    client, _ = gateway

    async def not_found(*args, **kwargs):
        return httpx.Response(
            404,
            json={"detail": "Product not found"},
        )

    monkeypatch.setattr(
        main.app.state.http_client,
        "request",
        not_found,
    )

    response = client.get("/products/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

def test_rate_limit_blocks_excess_requests(gateway, monkeypatch):
    client, _ = gateway

    monkeypatch.setattr(main, "REDIS_RATE_LIMIT", 2)

    first = client.get("/products")
    second = client.get("/products")
    third = client.get("/products")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == (
        "Rate limit exceeded. Try again later."
    )


def test_health_check_does_not_consume_rate_limit(gateway, monkeypatch):
    client, _ = gateway

    monkeypatch.setattr(main, "REDIS_RATE_LIMIT", 1)

    health = client.get("/health")
    product = client.get("/products")

    assert health.status_code == 200
    assert product.status_code == 200

def test_rate_limit_returns_503_when_redis_fails(gateway):
    client, _ = gateway

    class BrokenRedis:
        async def eval(self, *args):
            raise main.RedisError("Redis unavailable")

    main.app.state.redis = BrokenRedis()

    response = client.get("/products")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Rate limiting service is unavailable."
    )

def test_product_response_is_cached(gateway):
    client, captured = gateway

    first = client.get("/products")
    second = client.get("/products")

    assert first.status_code == 200
    assert second.status_code == 200

    # Product Service should only be called once.
    assert captured["calls"] == 1

    assert second.json() == first.json()

def test_product_cache_uses_different_query_parameters(gateway):
    client, captured = gateway

    first = client.get("/products?category=electronics")
    second = client.get("/products?category=clothing")

    assert first.status_code == 200
    assert second.status_code == 200

    # Different query parameters must call Product Service separately.
    assert captured["calls"] == 2

def test_product_cache_uses_query_parameters(gateway):
    client, captured = gateway

    first = client.get("/products?search=mouse")
    second = client.get("/products?search=mouse")
    third = client.get("/products?search=keyboard")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200

    # Same query uses cache; different query calls Product Service.
    assert captured["calls"] == 2

def test_authenticated_product_requests_bypass_cache(gateway):
    client, captured = gateway

    headers = {"Authorization": "Bearer test-token"}

    first = client.get("/products", headers=headers)
    second = client.get("/products", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200

    # Both authenticated requests must reach Product Service.
    assert captured["calls"] == 2

def test_admin_product_requests_bypass_cache(gateway):
    client, captured = gateway

    headers = {"Authorization": "Bearer admin-test-token"}

    first = client.get("/products/admin/all", headers=headers)
    second = client.get("/products/admin/all", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200

    # Both admin requests must reach Product Service.
    assert captured["calls"] == 2