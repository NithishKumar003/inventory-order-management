
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def gateway(monkeypatch):
    """Test the gateway with a fake downstream service."""
    captured = {}

    service_urls = {
        "AUTH_SERVICE_URL": "http://auth.test",
        "PRODUCT_SERVICE_URL": "http://product.test",
        "INVENTORY_SERVICE_URL": "http://inventory.test",
        "CART_SERVICE_URL": "http://cart.test",
        "ORDER_SERVICE_URL": "http://order.test",
        "PAYMENT_SERVICE_URL": "http://payment.test",
    }

    for setting, url in service_urls.items():
        monkeypatch.setattr(main, setting, url)

    def handler(request):
        captured["method"] = request.method
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

    yield client, captured

    client.close()
    import asyncio
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


def test_authorization_header_is_forwarded(gateway):
    client, captured = gateway

    response = client.get(
        "/orders",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert captured["headers"]["authorization"] == "Bearer test-token"


def test_downstream_response_is_preserved(gateway):
    client, _ = gateway

    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == {"message": "downstream response"}
    assert response.headers["x-downstream"] == "received"


@pytest.mark.parametrize(
    ("path", "service_setting", "error_message"),
    [
        ("/auth/login", "AUTH_SERVICE_URL",
         "Authentication service is unavailable."),
        ("/products", "PRODUCT_SERVICE_URL",
         "Product service is unavailable."),
        ("/inventory/1", "INVENTORY_SERVICE_URL",
         "Inventory service is unavailable."),
        ("/cart", "CART_SERVICE_URL",
         "Cart service is unavailable."),
        ("/orders", "ORDER_SERVICE_URL",
         "Order service is unavailable."),
        ("/payments/checkout", "PAYMENT_SERVICE_URL",
         "Payment service is unavailable."),
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
