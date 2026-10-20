"""
NetPulse Demo Store - Order Processing & Storage Engine.

Handles simulated ecommerce order placement, validation, cart totals,
and thread-safe persistent logging into results/orders.json.
Guarantees consistent order handling across all distributed backend nodes.
"""

import json
import os
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple

from .products import get_product_by_id


ORDERS_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "results",
        "orders.json",
    )
)

_orders_lock = threading.Lock()


def load_orders() -> List[Dict]:
    """Thread-safe retrieval of placed orders from shared orders.json."""
    with _orders_lock:
        if not os.path.exists(ORDERS_FILE):
            return []
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


def save_orders(orders: List[Dict]) -> None:
    """Thread-safe persistence of orders list into shared orders.json."""
    with _orders_lock:
        os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
        try:
            with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(orders, f, indent=2)
        except Exception as exc:
            print(f"[!] Warning: failed to save orders.json: {exc}")


def create_order(
    customer_name: str,
    email: str,
    address: str,
    items: List[Dict],
    serving_backend: str,
    payment_method: str = "Simulated Card",
) -> Tuple[bool, Dict, Optional[str]]:
    """
    Validate and process a simulated customer order.

    Returns: (success: bool, order_data: dict, error_message: Optional[str])
    """
    if not customer_name or not customer_name.strip():
        return False, {}, "Customer name is required."

    if not email or "@" not in email:
        return False, {}, "Valid email address is required."

    if not items or len(items) == 0:
        return False, {}, "Shopping cart is empty. Add at least one product."

    validated_items = []
    subtotal = 0.0

    for item in items:
        prod_id = item.get("product_id") or item.get("id")
        qty = item.get("quantity")
        if qty is None:
            qty = item.get("qty", 1)

        if not prod_id:
            return False, {}, "Invalid cart item: missing product_id."

        try:
            qty = int(qty)
            if qty <= 0:
                return False, {}, f"Invalid quantity '{qty}' for item {prod_id}."
        except (ValueError, TypeError):
            return False, {}, f"Invalid quantity value for item {prod_id}."

        product = get_product_by_id(prod_id)
        if not product:
            return False, {}, f"Product '{prod_id}' not found in catalogue."

        line_total = round(product["price"] * qty, 2)
        subtotal += line_total

        validated_items.append({
            "product_id": product["id"],
            "name": product["name"],
            "unit_price": product["price"],
            "quantity": qty,
            "line_total": line_total,
        })

    tax = round(subtotal * 0.08, 2)
    shipping = 0.0 if subtotal >= 99.0 else 15.0
    total = round(subtotal + tax + shipping, 2)

    # Unique order identifier
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    timestamp = time.time()

    order_record = {
        "order_id": order_id,
        "status": "CONFIRMED",
        "timestamp": timestamp,
        "date_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
        "customer": {
            "name": customer_name.strip(),
            "email": email.strip(),
            "address": address.strip() if address else "127.0.0.1 Local Lab Suite",
        },
        "payment": {
            "method": payment_method,
            "note": "SIMULATED TRANSACTION — NO REAL PAYMENT REQUIRED",
        },
        "items": validated_items,
        "summary": {
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping,
            "total": total,
            "item_count": sum(it["quantity"] for it in validated_items),
        },
        "network_telemetry": {
            "serving_backend": serving_backend,
            "processed_at": timestamp,
        },
    }

    # Persist in shared JSON storage
    all_orders = load_orders()
    all_orders.insert(0, order_record)
    save_orders(all_orders[:200])  # keep last 200 orders

    return True, order_record, None
