import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL",
    "http://127.0.0.1:8001",
)

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://127.0.0.1:8002",
)

INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL",
    "http://127.0.0.1:8003",
)

CART_SERVICE_URL = os.getenv(
    "CART_SERVICE_URL",
    "http://127.0.0.1:8004",
)

ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL",
    "http://127.0.0.1:8005",
)

PAYMENT_SERVICE_URL = os.getenv(
    "PAYMENT_SERVICE_URL",
    "http://127.0.0.1:8006",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http_client.aclose()

app = FastAPI(
    title="Inventory Management - API Gateway",
    description="Central entry point for the inventory microservices.",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "api-gateway",
    }

async def forward_auth_request(request: Request, path: str):
    client = request.app.state.http_client
    target_url = f"{AUTH_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"

    body = await request.body()

    try:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=list(request.query_params.multi_items()),
            content=body,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() not in {
                    "host",
                    "content-length",
                    "connection",
            }},
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Authentication service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in excluded_headers
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )

@app.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def auth_gateway(path: str, request: Request):
    return await forward_auth_request(request, path)

@app.get("/products/health")
async def product_health(request: Request):
    client = request.app.state.http_client

    try:
        response = await client.get(
            f"{PRODUCT_SERVICE_URL.rstrip('/')}/health"
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Product service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get(
            "content-type", "application/json"
        ),
    )

@app.api_route(
    "/products",
    methods=["GET", "POST"],
)
@app.api_route(
    "/products/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def product_gateway(request: Request, path: str = ""):
    client = request.app.state.http_client
    target_url = f"{PRODUCT_SERVICE_URL.rstrip('/')}/products"

    if path:
        target_url = f"{target_url}/{path}"

    body = await request.body()

    try:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=list(request.query_params.multi_items()),
            content=body,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() not in {
                    "host",
                    "content-length",
                    "connection",
                }
            },
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Product service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in excluded_headers
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )

async def forward_inventory_request(request: Request, path: str):
    client = request.app.state.http_client
    target_url = f"{INVENTORY_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
    body = await request.body()

    try:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=list(request.query_params.multi_items()),
            content=body,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() not in {
                    "host",
                    "content-length",
                    "connection",
                }
            },
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Inventory service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in excluded_headers
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )

@app.get("/inventory/health")
async def inventory_health(request: Request):
    client = request.app.state.http_client

    try:
        response = await client.get(
            f"{INVENTORY_SERVICE_URL.rstrip('/')}/health"
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Inventory service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get(
            "content-type", "application/json"
        ),
    )

@app.api_route(
    "/inventory",
    methods=["GET", "POST"],
)
@app.api_route(
    "/inventory/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def inventory_gateway(request: Request, path: str = ""):
    return await forward_inventory_request(request, f"inventory/{path}")


async def forward_cart_request(request: Request, path: str):
    client = request.app.state.http_client
    target_url = f"{CART_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
    body = await request.body()

    try:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=list(request.query_params.multi_items()),
            content=body,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() not in {
                    "host",
                    "content-length",
                    "connection",
                }
            },
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Cart service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in excluded_headers
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )


@app.api_route(
    "/cart",
    methods=["GET", "POST", "DELETE"],
)
@app.api_route(
    "/cart/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@app.api_route(
    "/wishlist",
    methods=["GET", "POST", "DELETE"],
)
@app.api_route(
    "/wishlist/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)

async def cart_gateway(request: Request, path: str = ""):
    service_path = request.url.path.lstrip("/")

    if service_path == "cart/health":
        service_path = "health"

    return await forward_cart_request(request, service_path)


@app.get("/cart/health")
async def cart_health(request: Request):
    return await forward_cart_request(request, "health")

async def forward_order_request(request: Request, path: str):
    client = request.app.state.http_client
    target_url = (
        f"{ORDER_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
    )
    body = await request.body()

    try:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=list(request.query_params.multi_items()),
            content=body,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() not in {
                    "host",
                    "content-length",
                    "connection",
                }
            },
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Order service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in excluded_headers
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )

@app.get("/orders/health")
async def order_health(request: Request):
    return await forward_order_request(request, "health")

@app.api_route(
    "/orders",
    methods=["GET", "POST"],
)
@app.api_route(
    "/orders/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def order_gateway(request: Request, path: str = ""):
    return await forward_order_request(
        request,
        "orders" if not path else f"orders/{path}",
    )

@app.get("/payments/health")
async def payment_health(request: Request):
    return await forward_payment_request(request, "health")

async def forward_payment_request(request: Request, path: str):
    client = request.app.state.http_client
    target_url = (
        f"{PAYMENT_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
    )
    body = await request.body()

    try:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=list(request.query_params.multi_items()),
            content=body,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() not in {
                    "host",
                    "content-length",
                    "connection",
                }
            },
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Payment service is unavailable."}',
            status_code=503,
            media_type="application/json",
        )

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in excluded_headers
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )

async def payment_gateway(request: Request, path: str = ""):
    return await forward_payment_request(
        request,
        "payments" if not path else f"payments/{path}",
    )

@app.api_route(
    "/payments",
    methods=["GET", "POST"],
)
@app.api_route(
    "/payments/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def payment_gateway(request: Request, path: str = ""):
    return await forward_payment_request(
        request,
        "payments" if not path else f"payments/{path}",
    )
