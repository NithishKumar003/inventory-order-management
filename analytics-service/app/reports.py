import httpx

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import require_admin
from app.config import (
    PRODUCT_SERVICE_URL,
    INVENTORY_SERVICE_URL,
    ORDER_SERVICE_URL,
    PAYMENT_SERVICE_URL,
    RETURN_SERVICE_URL,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])
security = HTTPBearer()

async def fetch_service_data(
    service_url: str,
    endpoint: str,
    credentials: HTTPAuthorizationCredentials,
):
    url = f"{service_url}{endpoint}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {credentials.credentials}"
                },
            )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Request timed out while contacting {service_url}",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to service: {service_url}",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Service request failed: {endpoint}",
        )

    try:
        return response.json()

    except ValueError:
        raise HTTPException(
            status_code=502,
            detail=f"Invalid JSON response from service: {endpoint}",
        )
        
@router.get("/overview")
async def get_admin_overview(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(require_admin),
):
    products = await fetch_all_products(credentials)

    inventory = await fetch_service_data(
        INVENTORY_SERVICE_URL,
        "/inventory",
        credentials,
    )

    low_stock = await fetch_service_data(
        INVENTORY_SERVICE_URL,
        "/inventory/low-stock",
        credentials,
    )

    orders = await fetch_service_data(
        ORDER_SERVICE_URL,
        "/orders/admin/all",
        credentials,
    )

    payments = await fetch_service_data(
        PAYMENT_SERVICE_URL,
        "/admin/payments",
        credentials,
    )

    refunds = await fetch_service_data(
        PAYMENT_SERVICE_URL,
        "/admin/refunds",
        credentials,
    )

    returns = await fetch_service_data(
        RETURN_SERVICE_URL,
        "/returns/admin",
        credentials,
    )

    order_statuses = {}
    for order in orders:
        status = order["status"]
        order_statuses[status] = order_statuses.get(status, 0) + 1

    delivered_revenue = sum(
        float(order["total_amount"])
        for order in orders
        if order["status"] == "Delivered"
    )

    total_order_value = sum(
        float(order["total_amount"])
        for order in orders
    )

    successful_payments = [
        payment for payment in payments
        if payment["status"] == "SUCCESS"
    ]

    successful_refunds = [
        refund for refund in refunds
        if refund["status"] == "SUCCEEDED"
    ]

    return {
        "products": {
            "total": len(products),
        },
        "inventory": {
            "total_products": len(inventory),
            "total_units": sum(
                int(item["quantity"]) for item in inventory
            ),
            "low_stock_products": len(low_stock),
        },
        "orders": {
            "total": len(orders),
            "by_status": order_statuses,
            "total_order_value": round(total_order_value, 2),
            "delivered_revenue": round(delivered_revenue, 2),
        },
        "payments": {
            "total": len(payments),
            "successful": len(successful_payments),
            "successful_amount": round(
                sum(float(payment["amount"]) for payment in successful_payments),
                2,
            ),
        },
        "refunds": {
            "total": len(refunds),
            "successful": len(successful_refunds),
            "successful_amount": round(
                sum(float(refund["amount"]) for refund in successful_refunds),
                2,
            ),
        },
        "returns": {
            "total": len(returns),
        },
    }
    
async def fetch_all_products(
    credentials: HTTPAuthorizationCredentials,
):
    all_products = []
    skip = 0
    limit = 100

    while True:
        products = await fetch_service_data(
            PRODUCT_SERVICE_URL,
            f"/products?skip={skip}&limit={limit}",
            credentials,
        )

        if not isinstance(products, list):
            raise HTTPException(
                status_code=502,
                detail="Invalid product list received from Product Service",
            )

        all_products.extend(products)

        if len(products) < limit:
            break

        skip += limit

    return all_products

async def fetch_all_admin_products(
    credentials: HTTPAuthorizationCredentials,
):
    all_products = []
    skip = 0
    limit = 100

    while True:
        products = await fetch_service_data(
            PRODUCT_SERVICE_URL,
            f"/products/admin/all?skip={skip}&limit={limit}",
            credentials,
        )

        if not isinstance(products, list):
            raise HTTPException(
                status_code=502,
                detail="Invalid product list received from Product Service",
            )

        all_products.extend(products)

        if len(products) < limit:
            break

        skip += limit

    return all_products

@router.get("/sales")
async def get_sales_report(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(require_admin),
):
    orders = await fetch_service_data(
        ORDER_SERVICE_URL,
        "/orders/admin/all",
        credentials,
    )

    total_orders = len(orders)
    
    non_cancelled_orders = [
        order for order in orders
        if order["status"] != "Cancelled"
    ]

    completed_sales = [
        order for order in orders
        if order["status"] == "Delivered"
    ]

    orders_by_status = {}
    revenue_by_status = {}

    for order in orders:
        status = order["status"]
        amount = float(order["total_amount"])

        orders_by_status[status] = (
            orders_by_status.get(status, 0) + 1
        )

        revenue_by_status[status] = (
            revenue_by_status.get(status, 0) + amount
        )

    delivered_orders = [
        order for order in orders
        if order["status"] == "Delivered"
    ]

    delivered_revenue = sum(
        float(order["total_amount"])
        for order in delivered_orders
    )

    total_discounts = sum(
        float(order["discount_amount"])
        for order in orders
    )

    total_shipping = sum(
        float(order["shipping_amount"])
        for order in orders
    )

    return {
        "total_orders": total_orders,
        "non_cancelled_orders": len(non_cancelled_orders),
        "non_cancelled_order_value": round(
            sum(
                float(order["total_amount"])
                for order in non_cancelled_orders
            ),
            2,
        ),
        "completed_sales_count": len(completed_sales),
        "completed_sales_revenue": round(
            sum(
                float(order["total_amount"])
                for order in completed_sales
            ),
            2,
        ),
        "orders_by_status": orders_by_status,
        "revenue_by_status": {
            status: round(amount, 2)
            for status, amount in revenue_by_status.items()
        },
        "delivered_orders": len(delivered_orders),
        "delivered_revenue": round(delivered_revenue, 2),
        "total_discounts": round(total_discounts, 2),
        "total_shipping_charges": round(total_shipping, 2),
        "average_order_value": round(
            sum(float(order["total_amount"]) for order in orders)
            / total_orders,
            2,
        ) if total_orders else 0,
    }
    
@router.get("/inventory")
async def get_inventory_report(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(require_admin),
):
    inventory = await fetch_service_data(
        INVENTORY_SERVICE_URL,
        "/inventory",
        credentials,
    )

    low_stock = await fetch_service_data(
        INVENTORY_SERVICE_URL,
        "/inventory/low-stock",
        credentials,
    )

    products = await fetch_all_products(credentials)

    product_lookup = {
        product["id"]: product
        for product in products
    }

    unmatched_inventory = []
    product_details = []
    total_units = 0
    total_stock_value = 0
    out_of_stock_products = 0

    for item in inventory:
        quantity = item["quantity"]

        # Count stock from every inventory record.
        total_units += quantity

        product = product_lookup.get(item["product_id"])

        if product is None:
            unmatched_inventory.append({
                "product_id": item["product_id"],
                "quantity": quantity,
            })
            continue

        price = product["price"]

        total_stock_value += quantity * price

        if quantity == 0:
            out_of_stock_products += 1

        product_details.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "sku": product["sku"],
            "price": price,
            "quantity": quantity,
            "stock_value": round(quantity * price, 2),
            "is_active": product["is_active"],
        })

    return {
        "total_inventory_records": len(inventory),
        "total_units": total_units,
        "low_stock_products": len(low_stock),
        "out_of_stock_products": out_of_stock_products,
        "total_stock_value": round(total_stock_value, 2),
        "products": product_details,
        "unmatched_inventory_records": unmatched_inventory,
    }
    
@router.get("/payments")
async def get_payment_report(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(require_admin),
):
    payments = await fetch_service_data(
        PAYMENT_SERVICE_URL,
        "/admin/payments",
        credentials,
    )

    refunds = await fetch_service_data(
        PAYMENT_SERVICE_URL,
        "/admin/refunds",
        credentials,
    )

    payment_statuses = {}
    refund_statuses = {}

    for payment in payments:
        status = payment["status"]
        payment_statuses[status] = (
            payment_statuses.get(status, 0) + 1
        )

    for refund in refunds:
        status = refund["status"]
        refund_statuses[status] = (
            refund_statuses.get(status, 0) + 1
        )

    successful_payments = [
        payment for payment in payments
        if payment["status"] == "SUCCESS"
    ]

    successful_refunds = [
        refund for refund in refunds
        if refund["status"] == "SUCCEEDED"
    ]

    return {
        "payments": {
            "total": len(payments),
            "by_status": payment_statuses,
            "successful_count": len(successful_payments),
            "successful_amount": round(
                sum(
                    float(payment["amount"])
                    for payment in successful_payments
                ),
                2,
            ),
        },
        "refunds": {
            "total": len(refunds),
            "by_status": refund_statuses,
            "successful_count": len(successful_refunds),
            "successful_amount": round(
                sum(
                    float(refund["amount"])
                    for refund in successful_refunds
                ),
                2,
            ),
        },
    }
    
@router.get("/returns")
async def get_returns_report(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(require_admin),
):
    returns = await fetch_service_data(
        RETURN_SERVICE_URL,
        "/returns/admin",
        credentials,
    )

    returns_by_status = {}
    refunds_by_status = {}

    total_returned_quantity = 0
    total_refund_amount = 0.0
    successful_refund_amount = 0.0

    for item in returns:
        return_status = item["status"]
        returns_by_status[return_status] = (
            returns_by_status.get(return_status, 0) + 1
        )

        total_returned_quantity += int(item["quantity"])

        refund_amount = float(item["refund_amount"] or 0)
        total_refund_amount += refund_amount

        refund_status = item["refund_status"]

        if refund_status:
            refunds_by_status[refund_status] = (
                refunds_by_status.get(refund_status, 0) + 1
            )

            if refund_status == "SUCCEEDED":
                successful_refund_amount += refund_amount

    return {
        "total_return_requests": len(returns),
        "returns_by_status": returns_by_status,
        "total_returned_quantity": total_returned_quantity,
        "total_refund_amount": round(total_refund_amount, 2),
        "refunds_by_status": refunds_by_status,
        "successful_refund_amount": round(
            successful_refund_amount, 2
        ),
    }
    
@router.get("/products")
async def get_product_performance_report(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: dict = Depends(require_admin),
):
    all_products = await fetch_all_admin_products(credentials)

    products = [
        product for product in all_products
        if product["is_active"] is True
    ]

    inactive_products = [
        product for product in all_products
        if product["is_active"] is False
    ]

    inventory = await fetch_service_data(
        INVENTORY_SERVICE_URL,
        "/inventory",
        credentials,
    )

    inventory_product_ids = {
        item["product_id"]
        for item in inventory
    }

    products_by_category = {}
    products_by_brand = {}

    for product in products:
        category = product["category"]
        brand = product["brand"] or "Unspecified"

        products_by_category[category] = (
            products_by_category.get(category, 0) + 1
        )

        products_by_brand[brand] = (
            products_by_brand.get(brand, 0) + 1
        )

    prices = [
        float(product["price"])
        for product in products
    ]

    products_without_inventory = [
        {
            "product_id": product["id"],
            "product_name": product["name"],
            "sku": product["sku"],
        }
        for product in products
        if product["id"] not in inventory_product_ids
    ]

    return {
        "total_active_products": len(products),
        "inactive_products": len(inactive_products),
        "products_by_category": products_by_category,
        "products_by_brand": products_by_brand,
        "price_statistics": {
            "minimum_price": round(min(prices), 2) if prices else 0,
            "maximum_price": round(max(prices), 2) if prices else 0,
            "average_price": round(
                sum(prices) / len(prices), 2
            ) if prices else 0,
        },
        "products_without_inventory": products_without_inventory,
    }