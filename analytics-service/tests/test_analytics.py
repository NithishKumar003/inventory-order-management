import pytest
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.main import app
from app.auth import require_admin

client = TestClient(app)


def override_admin():
    return {
        "id": 1,
        "role": "admin",
    }


app.dependency_overrides[require_admin] = override_admin


def test_analytics_overview_returns_report():
    mock_products = [
        {"id": 1, "name": "Product A"},
        {"id": 2, "name": "Product B"},
    ]

    mock_inventory = [
        {"product_id": 1, "quantity": 20},
        {"product_id": 2, "quantity": 5},
    ]

    mock_low_stock = [
        {"product_id": 2, "quantity": 5},
    ]

    mock_orders = [
        {"status": "Delivered", "total_amount": 100},
        {"status": "Confirmed", "total_amount": 50},
        {"status": "Cancelled", "total_amount": 25},
    ]

    mock_payments = [
        {"status": "SUCCESS", "amount": 100},
        {"status": "FAILED", "amount": 50},
    ]

    mock_refunds = [
        {"status": "SUCCEEDED", "amount": 20},
    ]

    mock_returns = [
        {"id": 1, "status": "COMPLETED"},
    ]

    async def fake_fetch_service_data(service_url, endpoint, credentials):
        if endpoint == "/inventory":
            return mock_inventory
        if endpoint == "/inventory/low-stock":
            return mock_low_stock
        if endpoint == "/orders/admin/all":
            return mock_orders
        if endpoint == "/admin/payments":
            return mock_payments
        if endpoint == "/admin/refunds":
            return mock_refunds
        if endpoint == "/returns/admin":
            return mock_returns

        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    async def fake_fetch_all_products(credentials):
        return mock_products

    app.dependency_overrides[require_admin] = override_admin

    with (
        patch(
            "app.reports.fetch_service_data",
            new=AsyncMock(side_effect=fake_fetch_service_data),
        ),
        patch(
            "app.reports.fetch_all_products",
            new=AsyncMock(side_effect=fake_fetch_all_products),
        ),
    ):
        response = client.get(
            "/analytics/overview",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["products"]["total"] == 2
    assert data["inventory"]["total_products"] == 2
    assert data["inventory"]["total_units"] == 25
    assert data["inventory"]["low_stock_products"] == 1

    assert data["orders"]["total"] == 3
    assert data["orders"]["by_status"]["Delivered"] == 1
    assert data["orders"]["delivered_revenue"] == 100.0
    assert data["orders"]["total_order_value"] == 175.0

    assert data["payments"]["successful"] == 1
    assert data["payments"]["successful_amount"] == 100.0

    assert data["refunds"]["successful"] == 1
    assert data["refunds"]["successful_amount"] == 20.0

    assert data["returns"]["total"] == 1


def test_analytics_overview_requires_authentication():
    response = client.get("/analytics/overview")

    assert response.status_code in (401, 403)
    
def test_inventory_report_returns_correct_totals():

    mock_inventory = [
        {"product_id": 1, "quantity": 10},
        {"product_id": 2, "quantity": 5},
        {"product_id": 999, "quantity": 50},
    ]

    mock_low_stock = [
        {"product_id": 2, "quantity": 5},
    ]

    mock_products = [
        {
            "id": 1,
            "name": "Laptop",
            "sku": "LAP-001",
            "price": 1000,
            "is_active": True,
        },
        {
            "id": 2,
            "name": "Mouse",
            "sku": "MOU-001",
            "price": 200,
            "is_active": True,
        },
    ]

    async def fake_fetch_service_data(service_url, endpoint, credentials):
        if endpoint == "/inventory":
            return mock_inventory

        if endpoint == "/inventory/low-stock":
            return mock_low_stock

        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    async def fake_fetch_all_products(credentials):
        return mock_products

    with (
        patch(
            "app.reports.fetch_service_data",
            new=AsyncMock(side_effect=fake_fetch_service_data),
        ),
        patch(
            "app.reports.fetch_all_products",
            new=AsyncMock(side_effect=fake_fetch_all_products),
        ),
    ):
        response = client.get(
            "/analytics/inventory",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_inventory_records"] == 3
    assert data["total_units"] == 65
    assert data["low_stock_products"] == 1
    assert data["out_of_stock_products"] == 0
    assert data["total_stock_value"] == 11000.0

    assert len(data["products"]) == 2
    assert len(data["unmatched_inventory_records"]) == 1

    assert data["unmatched_inventory_records"][0] == {
        "product_id": 999,
        "quantity": 50,
    }
    
def test_payment_report_returns_correct_totals():

    mock_payments = [
        {"status": "SUCCESS", "amount": 100},
        {"status": "SUCCESS", "amount": 150},
        {"status": "FAILED", "amount": 50},
        {"status": "CANCELLED", "amount": 25},
    ]

    mock_refunds = [
        {"status": "SUCCEEDED", "amount": 30},
        {"status": "FAILED", "amount": 10},
        {"status": "PENDING", "amount": 5},
    ]

    async def fake_fetch_service_data(service_url, endpoint, credentials):
        if endpoint == "/admin/payments":
            return mock_payments

        if endpoint == "/admin/refunds":
            return mock_refunds

        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    with patch(
        "app.reports.fetch_service_data",
        new=AsyncMock(side_effect=fake_fetch_service_data),
    ):
        response = client.get(
            "/analytics/payments",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["payments"]["total"] == 4
    assert data["payments"]["by_status"]["SUCCESS"] == 2
    assert data["payments"]["successful_count"] == 2
    assert data["payments"]["successful_amount"] == 250.0

    assert data["refunds"]["total"] == 3
    assert data["refunds"]["by_status"]["SUCCEEDED"] == 1
    assert data["refunds"]["successful_count"] == 1
    assert data["refunds"]["successful_amount"] == 30.0
    
def test_returns_report_returns_correct_totals():

    mock_returns = [
        {
            "status": "APPROVED",
            "quantity": 2,
            "refund_amount": 500,
            "refund_status": "SUCCEEDED",
        },
        {
            "status": "PENDING",
            "quantity": 1,
            "refund_amount": 200,
            "refund_status": "PENDING",
        },
        {
            "status": "REJECTED",
            "quantity": 3,
            "refund_amount": None,
            "refund_status": None,
        },
    ]

    async def fake_fetch_service_data(service_url, endpoint, credentials):
        if endpoint == "/returns/admin":
            return mock_returns

        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    with patch(
        "app.reports.fetch_service_data",
        new=AsyncMock(side_effect=fake_fetch_service_data),
    ):
        response = client.get(
            "/analytics/returns",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_return_requests"] == 3
    assert data["returns_by_status"]["APPROVED"] == 1
    assert data["returns_by_status"]["PENDING"] == 1
    assert data["returns_by_status"]["REJECTED"] == 1

    assert data["total_returned_quantity"] == 6
    assert data["total_refund_amount"] == 700.0

    assert data["refunds_by_status"]["SUCCEEDED"] == 1
    assert data["refunds_by_status"]["PENDING"] == 1

    assert data["successful_refund_amount"] == 500.0
    
def test_product_performance_report_returns_correct_totals():
    products = [
        {
            "id": 1,
            "name": "Laptop",
            "sku": "LAP-001",
            "category": "Computers",
            "brand": "Lenovo",
            "price": 50000,
            "is_active": True,
        },
        {
            "id": 2,
            "name": "Headphones",
            "sku": "AUD-001",
            "category": "Electronics",
            "brand": None,
            "price": 2000,
            "is_active": True,
        },
        {
            "id": 3,
            "name": "Old Keyboard",
            "sku": "KEY-001",
            "category": "Accessories",
            "brand": "Test Brand",
            "price": 1000,
            "is_active": False,
        },
    ]

    inventory = [
        {"product_id": 1, "quantity": 10},
    ]

    with patch(
        "app.reports.fetch_all_admin_products",
        new_callable=AsyncMock,
        return_value=products,
    ), patch(
        "app.reports.fetch_service_data",
        new_callable=AsyncMock,
        return_value=inventory,
    ):
        response = client.get(
            "/analytics/products",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_active_products"] == 2
    assert data["inactive_products"] == 1

    assert data["products_by_category"] == {
        "Computers": 1,
        "Electronics": 1,
    }

    assert data["products_by_brand"] == {
        "Lenovo": 1,
        "Unspecified": 1,
    }

    assert data["price_statistics"]["minimum_price"] == 2000
    assert data["price_statistics"]["maximum_price"] == 50000
    assert data["price_statistics"]["average_price"] == 26000

    assert data["products_without_inventory"][0]["product_id"] == 2
 
def test_sales_report_returns_correct_totals():
    mock_orders = [
        {
            "status": "Delivered",
            "total_amount": 100,
            "discount_amount": 10,
            "shipping_amount": 5,
        },
        {
            "status": "Confirmed",
            "total_amount": 200,
            "discount_amount": 20,
            "shipping_amount": 10,
        },
        {
            "status": "Cancelled",
            "total_amount": 50,
            "discount_amount": 0,
            "shipping_amount": 5,
        },
    ]

    async def fake_fetch_service_data(service_url, endpoint, credentials):
        if endpoint == "/orders/admin/all":
            return mock_orders

        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    with patch(
        "app.reports.fetch_service_data",
        new=AsyncMock(side_effect=fake_fetch_service_data),
    ):
        response = client.get(
            "/analytics/sales",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_orders"] == 3
    assert data["orders_by_status"] == {
        "Delivered": 1,
        "Confirmed": 1,
        "Cancelled": 1,
    }

    assert data["revenue_by_status"] == {
        "Delivered": 100.0,
        "Confirmed": 200.0,
        "Cancelled": 50.0,
    }

    assert data["delivered_orders"] == 1
    assert data["delivered_revenue"] == 100.0
    assert data["total_discounts"] == 30.0
    assert data["total_shipping_charges"] == 20.0
    assert data["average_order_value"] == round(350 / 3, 2)
    
    assert data["non_cancelled_orders"] == 2
    assert data["non_cancelled_order_value"] == 300.0
    assert data["completed_sales_count"] == 1
    assert data["completed_sales_revenue"] == 100.0
    
def test_sales_report_handles_service_timeout():
    with patch(
        "app.reports.fetch_service_data",
        new=AsyncMock(
            side_effect=__import__(
                "fastapi"
            ).HTTPException(
                status_code=504,
                detail="Request timed out",
            )
        ),
    ):
        response = client.get(
            "/analytics/sales",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 504
    assert response.json()["detail"] == "Request timed out"


def test_sales_report_handles_service_unavailable():
    with patch(
        "app.reports.fetch_service_data",
        new=AsyncMock(
            side_effect=__import__(
                "fastapi"
            ).HTTPException(
                status_code=503,
                detail="Unable to connect to service",
            )
        ),
    ):
        response = client.get(
            "/analytics/sales",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to connect to service"
    
def test_fetch_service_data_handles_timeout():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test-token",
    )

    with patch(
        "app.reports.httpx.AsyncClient"
    ) as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=__import__("httpx").TimeoutException(
                "Request timed out"
            )
        )

        with pytest.raises(HTTPException) as error:
            import asyncio
            asyncio.run(
                __import__("app.reports", fromlist=["fetch_service_data"])
                .fetch_service_data(
                    "http://127.0.0.1:8002",
                    "/products",
                    credentials,
                )
            )

    assert error.value.status_code == 504

def test_fetch_service_data_handles_invalid_json():
    import asyncio
    from unittest.mock import Mock

    from app.reports import fetch_service_data

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test-token",
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch("app.reports.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(HTTPException) as error:
            asyncio.run(
                fetch_service_data(
                    "http://127.0.0.1:8002",
                    "/products",
                    credentials,
                )
            )

    assert error.value.status_code == 502
    
def test_fetch_service_data_handles_non_200_response():
    import asyncio
    from unittest.mock import Mock

    from app.reports import fetch_service_data

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test-token",
    )

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Product not found"

    with patch("app.reports.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(HTTPException) as error:
            asyncio.run(
                fetch_service_data(
                    "http://127.0.0.1:8002",
                    "/products/999",
                    credentials,
                )
            )

    assert error.value.status_code == 502
    
def test_fetch_service_data_handles_connection_error():
    import asyncio
    import httpx

    from app.reports import fetch_service_data

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test-token",
    )

    with patch("app.reports.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(HTTPException) as error:
            asyncio.run(
                fetch_service_data(
                    "http://127.0.0.1:8002",
                    "/products",
                    credentials,
                )
            )

    assert error.value.status_code == 503