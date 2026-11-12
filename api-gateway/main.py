import os
import json
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from redis.exceptions import RedisError
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://127.0.0.1:8007",
)

REVIEW_SERVICE_URL = os.getenv(
    "REVIEW_SERVICE_URL",
    "http://127.0.0.1:8008",
)

RETURN_SERVICE_URL = os.getenv(
    "RETURN_SERVICE_URL",
    "http://127.0.0.1:8009",
)

ANALYTICS_SERVICE_URL = os.getenv(
    "ANALYTICS_SERVICE_URL",
    "http://127.0.0.1:8010",
)

REDIS_RATE_LIMIT = int(
    os.getenv("REDIS_RATE_LIMIT", "100")
)

REDIS_RATE_LIMIT_WINDOW = int(
    os.getenv("REDIS_RATE_LIMIT_WINDOW", "60")
)

PRODUCT_CACHE_TTL = int(
    os.getenv("PRODUCT_CACHE_TTL", "30")
)

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])

if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

return current
"""

def get_product_cache_key(request: Request) -> str:
    query_string = request.url.query

    cache_key = f"product_cache:{request.url.path}"

    if query_string:
        cache_key += f"?{query_string}"

    return cache_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=30.0)

    redis_url = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )

    app.state.redis = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    try:
        await app.state.redis.ping()
        print("API Gateway connected to Redis successfully.")

        yield

    finally:
        await app.state.redis.aclose()
        await app.state.http_client.aclose()

app = FastAPI(
    title="Inventory Management - API Gateway",
    description="Central entry point for the inventory microservices.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Do not rate-limit health checks.
    if request.url.path.endswith("/health"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"

    redis_key = f"rate_limit:{client_ip}"

    try:
        current_count = await request.app.state.redis.eval(
            RATE_LIMIT_SCRIPT,
            1,
            redis_key,
            REDIS_RATE_LIMIT_WINDOW,
        )

        if current_count > REDIS_RATE_LIMIT:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(REDIS_RATE_LIMIT_WINDOW),
                    "X-RateLimit-Limit": str(REDIS_RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(REDIS_RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, REDIS_RATE_LIMIT - current_count)
        )

        return response

    except RedisError:
        return Response(
            content='{"detail":"Rate limiting service is unavailable."}',
            status_code=503,
            media_type="application/json",
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

    cache_allowed = (
        request.method == "GET"
        and "authorization" not in request.headers
        and path != "admin/all"
        and not path.startswith("admin/")
    )

    cache_key = get_product_cache_key(request)

    if cache_allowed:
        try:
            cached_data = await request.app.state.redis.get(cache_key)

            if cached_data:
                cached_response = json.loads(cached_data)

                return Response(
                    content=cached_response["content"],
                    status_code=cached_response["status_code"],
                    headers=cached_response["headers"],
                )

        except (RedisError, json.JSONDecodeError):
            pass

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

    # Invalidate product cache after successful product mutations.
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and 200 <= upstream_response.status_code < 300
    ):
        try:
            async for key in request.app.state.redis.scan_iter(
                match="product_cache:*"
            ):
                await request.app.state.redis.delete(key)

        except RedisError:
            pass

    if cache_allowed and upstream_response.status_code == 200:
        try:
            cache_data = {
                "content": upstream_response.text,
                "status_code": upstream_response.status_code,
                "headers": response_headers,
            }

            await request.app.state.redis.setex(
                cache_key,
                PRODUCT_CACHE_TTL,
                json.dumps(cache_data),
            )

        except RedisError:
            pass

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
        "location",
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
    if path:
        inventory_path = f"inventory/{path}"
    else:
        inventory_path = "inventory"

    return await forward_inventory_request(request, inventory_path)

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

@app.api_route(
    "/coupons",
    methods=["GET", "POST"],
)
@app.api_route(
    "/coupons/{path:path}",
    methods=["GET", "POST", "PATCH"],
)
async def coupon_gateway(request: Request, path: str = ""):
    return await forward_order_request(
        request,
        "coupons" if not path else f"coupons/{path}",
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

async def forward_notification_request(request: Request, path: str):
    client = request.app.state.http_client
    target_url = (
        f"{NOTIFICATION_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
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
            content='{"detail":"Notification service is unavailable."}',
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


@app.get("/notifications/health")
async def notification_health(request: Request):
    return await forward_notification_request(request, "health")


@app.api_route(
    "/notifications",
    methods=["GET", "POST"],
)
@app.api_route(
    "/notifications/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def notification_gateway(request: Request, path: str = ""):
    return await forward_notification_request(
        request,
        "notifications/" if not path else f"notifications/{path}",
    )
async def forward_review_request(request: Request, path: str):
    client = request.app.state.http_client
    target_url = (
        f"{REVIEW_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
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
            content='{"detail":"Review service is unavailable."}',
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


@app.get("/reviews/health")
async def review_health(request: Request):
    return await forward_review_request(request, "health")


@app.api_route(
    "/reviews",
    methods=["GET", "POST"],
)
@app.api_route(
    "/reviews/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def review_gateway(request: Request, path: str = ""):
    gateway_path = request.url.path.strip("/")

    if gateway_path == "reviews":
        service_path = "reviews"
    elif gateway_path.startswith("reviews/products/"):
        service_path = gateway_path[len("reviews/"):]
    elif gateway_path == "reviews/me":
        service_path = "reviews/me"
    elif gateway_path.startswith("reviews/admin/"):
        service_path = "admin/reviews/" + gateway_path[len("reviews/admin/"):]
    elif gateway_path == "reviews/admin":
        service_path = "admin/reviews"
    else:
        service_path = gateway_path[len("reviews/"):]

    return await forward_review_request(request, service_path)

# ==============================
# RETURN SERVICE
# ==============================

async def forward_return_request(request: Request, path: str):
    client = request.app.state.http_client

    target_url = (
        f"{RETURN_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
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
            content='{"detail":"Return service is unavailable."}',
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


@app.get("/returns/health")
async def return_health(request: Request):
    return await forward_return_request(
        request,
        "health",
    )


@app.api_route(
    "/returns",
    methods=["GET", "POST"],
)
@app.api_route(
    "/returns/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def return_gateway(request: Request, path: str = ""):
    return await forward_return_request(
        request,
        "returns" if not path else f"returns/{path}",
    )

# ==============================
# ANALYTICS SERVICE
# ==============================

async def forward_analytics_request(request: Request, path: str):
    client = request.app.state.http_client

    target_url = (
        f"{ANALYTICS_SERVICE_URL.rstrip('/')}/{path.lstrip('/')}"
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
            content='{"detail":"Analytics service is unavailable."}',
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


@app.get("/analytics/health")
async def analytics_health(request: Request):
    return await forward_analytics_request(
        request,
        "health",
    )


@app.api_route(
    "/analytics",
    methods=["GET", "POST"],
)
@app.api_route(
    "/analytics/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def analytics_gateway(request: Request, path: str = ""):
    return await forward_analytics_request(
        request,
        "analytics" if not path else f"analytics/{path}",
    )