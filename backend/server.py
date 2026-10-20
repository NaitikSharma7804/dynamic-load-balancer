"""
Demo backend server for the Dynamic Load Balancer project.

Each backend can be started independently with:

    python -m backend.server --port 5001 --name b1 --delay-ms 50

The server provides:
    GET /health

for active health monitoring and accepts normal HTTP requests
on all other paths.
"""

import argparse
import asyncio
import random
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from backend.products import get_all_products, get_product_by_id, get_categories
from backend.orders import create_order, load_orders


app = FastAPI(
    title="Load Balancer Demo Backend",
    description="Backend server used for testing the load balancer.",
)


# -------------------------------------------------------------------
# Runtime configuration
# -------------------------------------------------------------------

START_TIME = time.monotonic()

SERVER_NAME = "backend"

DELAY_MS = 0

FAIL_RATE = 0.0


# -------------------------------------------------------------------
# Health endpoint
# -------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """
    Health-check endpoint.

    The load balancer periodically calls this endpoint to determine
    whether this backend is available.
    """

    return {
        "status": "ok",
        "name": SERVER_NAME,
        "load": 0,
        "uptime_s": int(
            time.monotonic() - START_TIME
        ),
    }


# -------------------------------------------------------------------
# Artificial simulation helper
# -------------------------------------------------------------------

async def _simulate_delay_and_failure():
    """Apply artificial delay and simulated failure if configured."""
    if DELAY_MS > 0:
        await asyncio.sleep(DELAY_MS / 1000)
    if FAIL_RATE > 0:
        if random.random() < FAIL_RATE:
            return JSONResponse(
                {
                    "status": "error",
                    "message": "Simulated backend failure",
                    "backend": SERVER_NAME,
                },
                status_code=500,
            )
    return None


# -------------------------------------------------------------------
# NetPulse Demo Store Application Endpoints
# -------------------------------------------------------------------

@app.get("/api/products")
async def list_products(search: str = None, category: str = None):
    """List products from shared catalogue with optional search and category filters."""
    sim_err = await _simulate_delay_and_failure()
    if sim_err:
        return sim_err
    products = get_all_products(search=search, category=category)
    return {
        "status": "success",
        "backend": SERVER_NAME,
        "total": len(products),
        "products": products,
    }


@app.get("/api/products/{product_id}")
async def get_single_product(product_id: str):
    """Retrieve details for a single product by ID."""
    sim_err = await _simulate_delay_and_failure()
    if sim_err:
        return sim_err
    product = get_product_by_id(product_id)
    if not product:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": f"Product '{product_id}' not found",
                "backend": SERVER_NAME,
            },
        )
    return {
        "status": "success",
        "backend": SERVER_NAME,
        "product": product,
    }


@app.get("/api/categories")
async def list_categories():
    """Retrieve all product categories with accurate live item counts."""
    sim_err = await _simulate_delay_and_failure()
    if sim_err:
        return sim_err
    return {
        "status": "success",
        "backend": SERVER_NAME,
        "categories": get_categories(),
    }


@app.post("/api/orders")
async def place_order(request: Request):
    """Process a simulated customer checkout order."""
    sim_err = await _simulate_delay_and_failure()
    if sim_err:
        return sim_err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Invalid JSON body provided.",
                "backend": SERVER_NAME,
            },
        )

    customer_name = body.get("customer_name", "")
    email = body.get("email", "")
    address = body.get("address", "")
    items = body.get("items", [])
    payment_method = body.get("payment_method", "Simulated Card")

    success, order_data, err_msg = create_order(
        customer_name=customer_name,
        email=email,
        address=address,
        items=items,
        serving_backend=SERVER_NAME,
        payment_method=payment_method,
    )

    if not success:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": err_msg,
                "backend": SERVER_NAME,
            },
        )

    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "message": "Order created successfully (Simulated Transaction)",
            "backend": SERVER_NAME,
            "order": order_data,
        },
    )


@app.get("/api/demo-info")
async def demo_info():
    """Retrieve backend telemetry and demo store state."""
    sim_err = await _simulate_delay_and_failure()
    if sim_err:
        return sim_err
    orders = load_orders()
    return {
        "status": "success",
        "backend": SERVER_NAME,
        "uptime_s": int(time.monotonic() - START_TIME),
        "delay_ms": DELAY_MS,
        "fail_rate": FAIL_RATE,
        "total_catalog_products": len(get_all_products()),
        "total_simulated_orders": len(orders),
        "architecture": "NetPulse Shared Immutable Catalog & Thread-Safe Persistent Orders",
    }


# -------------------------------------------------------------------
# Main request handler (Catch-all for synthetic testing)
# -------------------------------------------------------------------

@app.api_route(
    "/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "HEAD",
        "OPTIONS",
    ],
)
async def handle_request(
    path: str,
    request: Request,
):
    """
    Handle requests forwarded by the load balancer.

    Artificial delay and failure rate can be configured from
    the command line. This makes it possible to demonstrate:

    - different server speeds
    - least-connections behavior
    - backend failures
    - retry/failover
    """

    # ---------------------------------------------------------------
    # Artificial network/application delay
    # ---------------------------------------------------------------

    if DELAY_MS > 0:
        await asyncio.sleep(
            DELAY_MS / 1000
        )

    # ---------------------------------------------------------------
    # Artificial failure generation
    # ---------------------------------------------------------------

    if FAIL_RATE > 0:

        if random.random() < FAIL_RATE:

            return JSONResponse(
                {
                    "status": "error",
                    "message": "Simulated backend failure",
                    "backend": SERVER_NAME,
                },
                status_code=500,
            )

    # ---------------------------------------------------------------
    # Read forwarded headers
    # ---------------------------------------------------------------

    forwarded_for = request.headers.get(
        "X-Forwarded-For"
    )

    request_id = request.headers.get(
        "X-Request-ID"
    )

    algorithm = request.headers.get(
        "X-LB-Algorithm"
    )

    # ---------------------------------------------------------------
    # Return useful information for demonstration
    # ---------------------------------------------------------------

    return {
        "status": "success",
        "message": "Request served successfully",

        "backend": SERVER_NAME,

        "path": "/" + path,

        "method": request.method,

        "request_id": request_id,

        "client_ip": forwarded_for,

        "load_balancing_algorithm": algorithm,

        "delay_ms": DELAY_MS,

        "timestamp": time.time(),
    }


# -------------------------------------------------------------------
# Server startup
# -------------------------------------------------------------------

def main():
    """
    Parse command-line arguments and start the backend.
    """

    global SERVER_NAME
    global DELAY_MS
    global FAIL_RATE

    parser = argparse.ArgumentParser(
        description="Start a load-balancer demo backend."
    )

    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port on which the backend will listen.",
    )

    parser.add_argument(
        "--name",
        required=True,
        help="Backend name, for example b1.",
    )

    parser.add_argument(
        "--delay-ms",
        type=int,
        default=0,
        help="Artificial response delay in milliseconds.",
    )

    parser.add_argument(
        "--fail-rate",
        type=float,
        default=0.0,
        help="Probability of returning HTTP 500. Range: 0.0 to 1.0.",
    )

    args = parser.parse_args()

    if not 0.0 <= args.fail_rate <= 1.0:
        raise ValueError(
            "fail-rate must be between 0.0 and 1.0"
        )

    SERVER_NAME = args.name
    DELAY_MS = args.delay_ms
    FAIL_RATE = args.fail_rate

    print("=" * 60)
    print("Dynamic Load Balancer - Backend Server")
    print("=" * 60)
    print(f"Name      : {SERVER_NAME}")
    print(f"Port      : {args.port}")
    print(f"Delay     : {DELAY_MS} ms")
    print(f"Fail Rate : {FAIL_RATE}")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()