"""
tools/api_tools.py
All mock API tools the agent can call. Each function simulates a real
production API with realistic responses, error handling, and side effects.
"""

import random
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from data.loader import (
    load_orders,
    load_customers,
    load_products,
    load_knowledge_base
)

# Load data once
ORDERS_LIST = load_orders()
CUSTOMERS_LIST = load_customers()
PRODUCTS_LIST = load_products()
KNOWLEDGE_BASE_TEXT = load_knowledge_base()

# Convert to dictionary for fast lookup
ORDERS = {o["order_id"]: o for o in ORDERS_LIST}
CUSTOMERS = {c["customer_id"]: c for c in CUSTOMERS_LIST}
PRODUCTS = {p["product_id"]: p for p in PRODUCTS_LIST}

# Optional: simple KB structure (you can improve later)
KNOWLEDGE_BASE = {
    "full_text": KNOWLEDGE_BASE_TEXT
}

logger = logging.getLogger("shopwave.tools")


def _simulate_latency(min_ms: int = 50, max_ms: int = 300):
    """Simulate realistic API latency."""
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def _maybe_fail(failure_rate: float = 0.05) -> bool:
    """Randomly simulate API failures for realism."""
    return random.random() < failure_rate


# ─────────────────────────────────────────────
# READ TOOLS
# ─────────────────────────────────────────────

def get_order(order_id: str) -> dict:
    """
    Fetch order details by order ID.
    Returns order data or error dict.
    """
    _simulate_latency()
    if _maybe_fail():
        raise TimeoutError(f"get_order({order_id}): API timeout — retry recommended")

    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Order #{order_id} not found", "order_id": order_id}

    logger.info(f"[TOOL] get_order({order_id}) → status={order['status']}, amount=${order['amount']}")
    return {"success": True, "data": order}


def get_customer(customer_id: str) -> dict:
    """
    Fetch customer profile by customer ID.
    """
    _simulate_latency()
    if _maybe_fail():
        raise TimeoutError(f"get_customer({customer_id}): API timeout")

    customer = CUSTOMERS.get(str(customer_id))
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    logger.info(f"[TOOL] get_customer({customer_id}) → name={customer['name']}, tier={customer['tier']}")
    return {"success": True, "data": customer}

def get_customer_by_email(email: str):
    for c in CUSTOMERS.values():
        if c["email"] == email:
            return {"success": True, "data": c}
    return {"error": f"Customer with email {email} not found"}

def get_product(product_id: str) -> dict:
    """
    Fetch product details by product ID.
    """
    _simulate_latency()
    product = PRODUCTS.get(str(product_id))
    if not product:
        return {"error": f"Product {product_id} not found"}

    logger.info(f"[TOOL] get_product({product_id}) → name={product['name']}, return_window={product['return_window_days']}d")
    return {"success": True, "data": product}


def search_knowledge_base(query: str) -> dict:
    """
    Search internal KB for policy / FAQ information.
    Uses simple keyword matching (in production: vector search).
    """
    _simulate_latency(20, 100)
    query_lower = query.lower()

    matches = []
    for key, content in KNOWLEDGE_BASE.items():
        if any(word in query_lower for word in key.replace("_", " ").split()):
            matches.append({"topic": key, "content": content})

    # Fallback: scan content text
    if not matches:
        for key, content in KNOWLEDGE_BASE.items():
            if any(word in content.lower() for word in query_lower.split() if len(word) > 4):
                matches.append({"topic": key, "content": content})

    logger.info(f"[TOOL] search_knowledge_base('{query}') → {len(matches)} result(s)")
    return {
        "success": True,
        "query": query,
        "results": matches[:3],  # Top 3
        "count": len(matches),
    }


# ─────────────────────────────────────────────
# ACTION TOOLS
# ─────────────────────────────────────────────

def check_refund_eligibility(order_id: str) -> dict:
    """
    Determine whether an order qualifies for a refund.
    Checks: order status, delivery date, product return window.
    """
    _simulate_latency()

    order = ORDERS.get(str(order_id))
    if not order:
        return {"eligible": False, "reason": f"Order #{order_id} not found"}

    product = PRODUCTS.get(order["product_id"], {})
    return_window = product.get("return_window_days", 30)

    # Parse delivery date
    try:
        delivery_date = datetime.strptime(order["delivery_date"], "%Y-%m-%d")
        days_since = (datetime.now() - delivery_date).days
    except Exception:
        days_since = 0

    # Rules
    if order["status"] in ("processing",):
        result = {"eligible": True, "reason": "Order not yet shipped — full refund available", "amount": order["amount"]}
    elif order["status"] == "delayed":
        result = {"eligible": True, "reason": "Order delayed — eligible for full refund or reroute", "amount": order["amount"]}
    elif days_since > return_window:
        result = {"eligible": False, "reason": f"Return window of {return_window} days has passed ({days_since} days since delivery)"}
    else:
        result = {"eligible": True, "reason": f"Within {return_window}-day return window ({days_since} days elapsed)", "amount": order["amount"]}

    logger.info(f"[TOOL] check_refund_eligibility({order_id}) → eligible={result['eligible']}, reason={result['reason']}")
    return {"success": True, **result}


def issue_refund(order_id: str, amount: float, reason: str) -> dict:
    """
    ⚠️  DESTRUCTIVE ACTION: Issue a refund to the customer.
    Mutates order status in mock DB. Logs everything.
    """
    _simulate_latency(100, 500)

    order = ORDERS.get(str(order_id))
    if not order:
        return {"success": False, "error": f"Order #{order_id} not found — refund aborted"}

    if amount <= 0 or amount > order["amount"]:
        return {"success": False, "error": f"Invalid refund amount ${amount} (order total: ${order['amount']})"}

    # Mutate mock DB
    ORDERS[str(order_id)]["status"] = "refunded"
    refund_id = f"REF-{order_id}-{int(time.time())}"
    eta = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

    logger.warning(f"[TOOL] ⚠️  issue_refund({order_id}, ${amount}) → refund_id={refund_id}")
    return {
        "success": True,
        "refund_id": refund_id,
        "order_id": order_id,
        "amount_refunded": amount,
        "reason": reason,
        "estimated_arrival": eta,
        "message": f"Refund of ${amount:.2f} initiated. Expected by {eta}.",
    }


def send_reply(customer_email: str, subject: str, body: str) -> dict:
    """
    Send an email reply to the customer.
    In production: integrates with SendGrid / SES.
    """
    _simulate_latency(50, 200)

    if not customer_email or "@" not in customer_email:
        return {"success": False, "error": "Invalid customer email"}

    message_id = f"MSG-{int(time.time())}-{random.randint(1000,9999)}"
    logger.info(f"[TOOL] send_reply(to={customer_email}, subject='{subject}') → msg_id={message_id}")

    # Print to console for demo purposes
    print(f"\n{'─'*60}")
    print(f"📧 EMAIL SENT")
    print(f"To:      {customer_email}")
    print(f"Subject: {subject}")
    print(f"Body:    {body}")
    print(f"{'─'*60}\n")

    return {
        "success": True,
        "message_id": message_id,
        "to": customer_email,
        "subject": subject,
        "sent_at": datetime.now().isoformat(),
    }


def escalate(ticket_id: str, summary: str, priority: str, reason: str) -> dict:
    """
    Escalate a ticket to a human agent.
    priority: 'high' | 'medium' | 'low'
    """
    _simulate_latency()

    valid_priorities = ("high", "medium", "low")
    if priority not in valid_priorities:
        priority = "medium"

    escalation_id = f"ESC-{ticket_id}-{int(time.time())}"
    queue = {"high": "Tier-2 Urgent", "medium": "Tier-1 Standard", "low": "Tier-1 Backlog"}[priority]

    logger.warning(f"[TOOL] 🔺 escalate(ticket={ticket_id}, priority={priority}) → {escalation_id} → queue={queue}")
    return {
        "success": True,
        "escalation_id": escalation_id,
        "ticket_id": ticket_id,
        "priority": priority,
        "queue": queue,
        "summary": summary,
        "reason": reason,
        "created_at": datetime.now().isoformat(),
    }

# ─────────────────────────────────────────────
# TOOL REGISTRY (VERY IMPORTANT)
# ─────────────────────────────────────────────

TOOL_MAP = {
    "get_order": get_order,
    "get_customer": get_customer,
    "get_customer_by_email": get_customer_by_email,
    "get_product": get_product,
    "search_knowledge_base": search_knowledge_base,
    "check_refund_eligibility": check_refund_eligibility,
    "issue_refund": issue_refund,
    "send_reply": send_reply,
    "escalate": escalate,
}

ALL_TOOLS = [
    get_order,
    get_customer,
    get_customer_by_email,
    get_product,
    search_knowledge_base,
    check_refund_eligibility,
    issue_refund,
    send_reply,
    escalate,
]