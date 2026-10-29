
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db


# Use a separate in-memory database for all tests.
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def make_product(
    name="Wireless Mouse",
    sku="TEST-MOUSE-001",
    price=599.0,
    category="Electronics",
    brand="TestBrand",
):
    return {
        "name": name,
        "description": "A test product",
        "sku": sku,
        "price": price,
        "category": category,
        "brand": brand,
        "specifications": {"color": "Black"},
    }


def create_product(client, **overrides):
    data = make_product(**overrides)
    response = client.post("/products", json=data)
    assert response.status_code == 201, response.text
    return response.json()


# 1. Health check
def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "product-service",
    }


# 2. Create a product
def test_create_product(client):
    response = client.post(
        "/products",
        json=make_product(),
    )

    assert response.status_code == 201
    product = response.json()
    assert product["id"] > 0
    assert product["name"] == "Wireless Mouse"
    assert product["sku"] == "TEST-MOUSE-001"
    assert product["price"] == 599.0
    assert product["is_active"] is True
    assert product["specifications"]["color"] == "Black"


# 3. Reject duplicate SKU
def test_duplicate_sku_rejected(client):
    create_product(client)

    response = client.post(
        "/products",
        json=make_product(name="Another Mouse"),
    )

    assert response.status_code == 409


# 4. Reject invalid product data
@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "A"},
        {"sku": "X"},
        {"price": 0},
        {"price": -10},
        {"category": "A"},
    ],
)
def test_invalid_product_data_rejected(client, overrides):
    response = client.post(
        "/products",
        json=make_product(**overrides),
    )

    assert response.status_code == 422


# 5. List products
def test_list_products(client):
    create_product(client)
    create_product(
        client,
        name="USB Keyboard",
        sku="TEST-KEYBOARD-001",
        category="Accessories",
    )

    response = client.get("/products")

    assert response.status_code == 200
    products = response.json()
    assert len(products) == 2
    assert {product["sku"] for product in products} == {
        "TEST-MOUSE-001",
        "TEST-KEYBOARD-001",
    }


# 6. Get one product
def test_get_product(client):
    created = create_product(client)

    response = client.get(f"/products/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["sku"] == created["sku"]


# 7. Missing product returns 404
def test_get_missing_product(client):
    response = client.get("/products/99999")

    assert response.status_code == 404


# 8. Update a product
def test_update_product(client):
    created = create_product(client)

    response = client.put(
        f"/products/{created['id']}",
        json={
            "name": "Updated Mouse",
            "price": 799.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Mouse"
    assert response.json()["price"] == 799.0
    assert response.json()["sku"] == created["sku"]


# 9. Reject update with duplicate SKU
def test_update_duplicate_sku_rejected(client):
    first = create_product(client)
    second = create_product(
        client,
        name="USB Keyboard",
        sku="TEST-KEYBOARD-001",
    )

    response = client.put(
        f"/products/{second['id']}",
        json={"sku": first["sku"]},
    )

    assert response.status_code == 409


# 10. Updating a missing product returns 404
def test_update_missing_product(client):
    response = client.put(
        "/products/99999",
        json={"name": "Updated Product"},
    )

    assert response.status_code == 404


# 11. Soft-delete a product
def test_delete_product(client):
    created = create_product(client)

    response = client.delete(f"/products/{created['id']}")

    assert response.status_code == 200

    # Deleted products should no longer be accessible.
    response = client.get(f"/products/{created['id']}")
    assert response.status_code == 404


# 12. Deleting a missing product returns 404
def test_delete_missing_product(client):
    response = client.delete("/products/99999")

    assert response.status_code == 404


# 13. Search by product name
def test_search_products(client):
    create_product(client)
    create_product(
        client,
        name="USB Keyboard",
        sku="TEST-KEYBOARD-001",
        category="Accessories",
    )

    response = client.get("/products", params={"search": "Mouse"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Wireless Mouse"


# 14. Search by SKU
def test_search_by_sku(client):
    create_product(client)

    response = client.get(
        "/products",
        params={"search": "TEST-MOUSE"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# 15. Filter by category
def test_filter_by_category(client):
    create_product(client)
    create_product(
        client,
        name="Office Chair",
        sku="TEST-CHAIR-001",
        category="Furniture",
    )

    response = client.get(
        "/products",
        params={"category": "Furniture"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Office Chair"


# 16. Filter by brand
def test_filter_by_brand(client):
    create_product(client)
    create_product(
        client,
        name="Office Chair",
        sku="TEST-CHAIR-001",
        brand="OtherBrand",
    )

    response = client.get(
        "/products",
        params={"brand": "TestBrand"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["brand"] == "TestBrand"


# 17. Filter by minimum price
def test_filter_by_minimum_price(client):
    create_product(client, price=599.0)
    create_product(
        client,
        name="Premium Mouse",
        sku="TEST-PREMIUM-001",
        price=1299.0,
    )

    response = client.get(
        "/products",
        params={"min_price": 1000},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["price"] == 1299.0


# 18. Filter by maximum price
def test_filter_by_maximum_price(client):
    create_product(client, price=599.0)
    create_product(
        client,
        name="Premium Mouse",
        sku="TEST-PREMIUM-001",
        price=1299.0,
    )

    response = client.get(
        "/products",
        params={"max_price": 700},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["price"] == 599.0


# 19. Reject minimum price greater than maximum price
def test_invalid_price_range(client):
    response = client.get(
        "/products",
        params={"min_price": 1000, "max_price": 500},
    )

    assert response.status_code == 400


# 20. Sort products by price descending
def test_sort_products_by_price_descending(client):
    create_product(client, price=599.0)
    create_product(
        client,
        name="Premium Mouse",
        sku="TEST-PREMIUM-001",
        price=1299.0,
    )

    response = client.get(
        "/products",
        params={"sort_by": "price", "sort_order": "desc"},
    )

    assert response.status_code == 200
    prices = [product["price"] for product in response.json()]
    assert prices == sorted(prices, reverse=True)


# 21. Reject an unsupported sort field
def test_invalid_sort_field(client):
    response = client.get(
        "/products",
        params={"sort_by": "unsupported_field"},
    )

    assert response.status_code == 400


# 22. Reject an unsupported sort order
def test_invalid_sort_order(client):
    response = client.get(
        "/products",
        params={"sort_order": "sideways"},
    )

    assert response.status_code == 400


# 23. Pagination
def test_product_pagination(client):
    create_product(client)
    create_product(
        client,
        name="USB Keyboard",
        sku="TEST-KEYBOARD-001",
    )
    create_product(
        client,
        name="Office Chair",
        sku="TEST-CHAIR-001",
        category="Furniture",
    )

    response = client.get(
        "/products",
        params={"skip": 1, "limit": 1, "sort_by": "id"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# 24. Reject invalid pagination values
@pytest.mark.parametrize(
    "params",
    [
        {"skip": -1},
        {"limit": 0},
        {"limit": 101},
    ],
)
def test_invalid_pagination_rejected(client, params):
    response = client.get("/products", params=params)

    assert response.status_code == 422


# 25. In-stock filtering includes products with stock
def test_filter_in_stock_products(client, monkeypatch):
    first = create_product(client)
    second = create_product(
        client,
        name="USB Keyboard",
        sku="TEST-KEYBOARD-001",
    )

    stock = {
        first["id"]: 5,
        second["id"]: 0,
    }

    monkeypatch.setattr(
        "app.main.get_stock_quantity",
        lambda product_id: stock.get(product_id, 0),
    )

    response = client.get(
        "/products",
        params={"in_stock": "true"},
    )

    assert response.status_code == 200
    products = response.json()
    assert [product["id"] for product in products] == [first["id"]]


# 26. In-stock filtering excludes products without stock
def test_filter_out_of_stock_products(client, monkeypatch):
    first = create_product(client)
    second = create_product(
        client,
        name="USB Keyboard",
        sku="TEST-KEYBOARD-001",
    )

    stock = {
        first["id"]: 5,
        second["id"]: 0,
    }

    monkeypatch.setattr(
        "app.main.get_stock_quantity",
        lambda product_id: stock.get(product_id, 0),
    )

    response = client.get(
        "/products",
        params={"in_stock": "false"},
    )

    assert response.status_code == 200
    products = response.json()
    assert [product["id"] for product in products] == [second["id"]]


# 27. Inventory timeout is translated into HTTP 503
def test_inventory_timeout_returns_503(client, monkeypatch):
    from fastapi import HTTPException

    def inventory_timeout(product_id):
        raise HTTPException(
            status_code=503,
            detail="Inventory Service timed out.",
        )

    monkeypatch.setattr(
        "app.main.get_stock_quantity",
        inventory_timeout,
    )

    # Create a product first, so the inventory filter has a product to check.
    create_product(client)

    response = client.get(
        "/products",
        params={"in_stock": "true"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Inventory Service timed out."
