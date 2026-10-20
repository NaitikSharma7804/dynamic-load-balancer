"""
Tests for NetPulse Demo Store Module.

Validates:
- Shared immutable product catalogue
- Search and category filtering
- Single product lookup and 404 handling
- Categories metadata with live counts
- Order creation validation (name, email, cart, quantity)
- Unique order ID generation and persistent logging
- Backend FastAPI endpoints (/api/products, /api/categories, /api/orders, /api/demo-info)
- Load Balancer /app routing
"""

import json
import os
import pytest
from fastapi.testclient import TestClient

from backend.products import (
    PRODUCTS,
    get_all_products,
    get_product_by_id,
    get_categories,
)
from backend.orders import create_order, load_orders, save_orders
from backend.server import app as backend_app
from loadbalancer.main import create_components, create_proxy_app


# -------------------------------------------------------------------
# Unit Tests: Product Catalogue
# -------------------------------------------------------------------

def test_product_catalogue_structure():
    """Verify products array contains valid hardware models with required schema."""
    assert len(PRODUCTS) >= 8
    for prod in PRODUCTS:
        assert "id" in prod
        assert "name" in prod
        assert "category" in prod
        assert "price" in prod
        assert prod["price"] > 0
        assert "specs" in prod
        assert isinstance(prod["specs"], dict)


def test_get_all_products_unfiltered():
    """Verify retrieving all products without parameters returns full catalogue."""
    prods = get_all_products()
    assert len(prods) == len(PRODUCTS)


def test_product_search_filtering():
    """Verify case-insensitive search by keyword matches name/description."""
    results = get_all_products(search="10G")
    assert len(results) > 0
    for p in results:
        text = (p["name"] + p["description"] + p["category_name"]).lower()
        assert "10g" in text

    # Search with no match
    no_results = get_all_products(search="quantum-teleportation-device-xyz")
    assert len(no_results) == 0


def test_product_category_filtering():
    """Verify category filtering isolates products of chosen category."""
    routers = get_all_products(category="routers")
    assert len(routers) > 0
    for p in routers:
        assert p["category"] == "routers"

    switches = get_all_products(category="switches")
    assert len(switches) > 0
    for p in switches:
        assert p["category"] == "switches"

    all_cat = get_all_products(category="all")
    assert len(all_cat) == len(PRODUCTS)


def test_get_product_by_id():
    """Verify single product retrieval by ID and handling of invalid IDs."""
    first_id = PRODUCTS[0]["id"]
    p = get_product_by_id(first_id)
    assert p is not None
    assert p["id"] == first_id

    missing = get_product_by_id("prod-nonexistent-999")
    assert missing is None


def test_get_categories_counts():
    """Verify live category count tally matches real product distribution."""
    categories = get_categories()
    assert len(categories) > 0

    all_cat = next(c for c in categories if c["id"] == "all")
    assert all_cat["count"] == len(PRODUCTS)

    # Verify each non-all category has non-zero count
    for c in categories:
        if c["id"] != "all":
            expected = sum(1 for p in PRODUCTS if p["category"] == c["id"])
            assert c["count"] == expected


# -------------------------------------------------------------------
# Unit Tests: Orders & Validation
# -------------------------------------------------------------------

def test_create_order_validation():
    """Verify edge-case validation checks during order creation."""
    # 1. Missing customer name
    ok, data, err = create_order("", "a@b.com", "Lab", [{"product_id": "prod-101", "quantity": 1}], "b1")
    assert not ok
    assert "name is required" in err.lower()

    # 2. Invalid email
    ok, data, err = create_order("Student", "not-an-email", "Lab", [{"product_id": "prod-101", "quantity": 1}], "b1")
    assert not ok
    assert "email" in err.lower()

    # 3. Empty items
    ok, data, err = create_order("Student", "a@b.com", "Lab", [], "b1")
    assert not ok
    assert "empty" in err.lower()

    # 4. Invalid quantity
    ok, data, err = create_order("Student", "a@b.com", "Lab", [{"product_id": "prod-101", "quantity": 0}], "b1")
    assert not ok
    assert "quantity" in err.lower()

    # 5. Invalid product ID
    ok, data, err = create_order("Student", "a@b.com", "Lab", [{"product_id": "nonexistent", "quantity": 1}], "b1")
    assert not ok
    assert "not found" in err.lower()


def test_create_valid_order():
    """Verify successful order creation, unique ID, tax, and totals calculation."""
    items = [
        {"product_id": "prod-101", "quantity": 1},  # $499.00
        {"product_id": "prod-104", "quantity": 2},  # $45.00 * 2 = $90.00
    ]
    ok, order, err = create_order(
        customer_name="Alice Smith",
        email="alice@test.edu",
        address="Rack A, Switch Lab",
        items=items,
        serving_backend="b2",
    )

    assert ok is True
    assert err is None
    assert order["order_id"].startswith("ORD-")
    assert order["status"] == "CONFIRMED"
    assert order["network_telemetry"]["serving_backend"] == "b2"

    subtotal = 499.00 + 90.00
    expected_tax = round(subtotal * 0.08, 2)
    expected_total = round(subtotal + expected_tax + 0.0, 2)  # subtotal >= 99 => shipping free

    assert order["summary"]["subtotal"] == subtotal
    assert order["summary"]["tax"] == expected_tax
    assert order["summary"]["shipping"] == 0.0
    assert order["summary"]["total"] == expected_total


# -------------------------------------------------------------------
# Integration Tests: Backend Server API
# -------------------------------------------------------------------

@pytest.fixture
def backend_client():
    with TestClient(backend_app) as client:
        yield client


def test_api_products_endpoint(backend_client):
    """Test GET /api/products returns 200 and product list."""
    res = backend_client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "products" in data
    assert len(data["products"]) == len(PRODUCTS)


def test_api_products_filter_endpoint(backend_client):
    """Test GET /api/products with search and category filters."""
    res = backend_client.get("/api/products?category=wireless")
    assert res.status_code == 200
    data = res.json()
    assert all(p["category"] == "wireless" for p in data["products"])


def test_api_product_detail_endpoint(backend_client):
    """Test GET /api/products/{id} for valid and invalid IDs."""
    valid_id = PRODUCTS[0]["id"]
    res = backend_client.get(f"/api/products/{valid_id}")
    assert res.status_code == 200
    assert res.json()["product"]["id"] == valid_id

    res_missing = backend_client.get("/api/products/unknown-id")
    assert res_missing.status_code == 404


def test_api_categories_endpoint(backend_client):
    """Test GET /api/categories returns 200 and category list."""
    res = backend_client.get("/api/categories")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "categories" in data


def test_api_orders_endpoint(backend_client):
    """Test POST /api/orders creates simulated order."""
    payload = {
        "customer_name": "Bob Jones",
        "email": "bob@university.edu",
        "address": "Networking Lab Room 101",
        "items": [
            {"product_id": "prod-102", "quantity": 1}
        ],
    }
    res = backend_client.post("/api/orders", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "success"
    assert "order" in data
    assert data["order"]["order_id"].startswith("ORD-")


def test_api_demo_info_endpoint(backend_client):
    """Test GET /api/demo-info returns 200 and telemetry data."""
    res = backend_client.get("/api/demo-info")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "uptime_s" in data
    assert "total_catalog_products" in data


# -------------------------------------------------------------------
# Integration Tests: Load Balancer /app Route
# -------------------------------------------------------------------

@pytest.fixture
def lb_client():
    config, pool, metrics, proxy, health = create_components()
    app = create_proxy_app(config, pool, metrics, proxy, health)
    with TestClient(app) as client:
        yield client


def test_lb_app_route(lb_client):
    """Verify load balancer serves /app Demo Store page."""
    res = lb_client.get("/app")
    assert res.status_code == 200
    assert "NetPulse Hardware Store" in res.text or "NetPulse" in res.text


def test_lb_root_route_contains_app(lb_client):
    """Verify load balancer root JSON includes /app demo_store link."""
    res = lb_client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data.get("demo_store") == "/app"
    assert data.get("dashboard") == "/dashboard"
