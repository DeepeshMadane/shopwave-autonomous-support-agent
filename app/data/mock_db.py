"""
Mock database for ShopWave — simulates order, customer, product data.
"""

ORDERS = {
    "123": {
        "order_id": "123",
        "customer_id": "C001",
        "product_id": "P001",
        "status": "delayed",
        "amount": 49.99,
        "expected_delivery": "2024-01-20",
        "carrier": "FedEx",
        "tracking": "FX123456789",
        "items": ["Blue Sneakers (Size 10)"],
    },
    "456": {
        "order_id": "456",
        "customer_id": "C002",
        "product_id": "P002",
        "status": "delivered",
        "amount": 129.99,
        "expected_delivery": "2024-01-15",
        "carrier": "UPS",
        "tracking": "UP987654321",
        "items": ["Wireless Headphones"],
    },
    "789": {
        "order_id": "789",
        "customer_id": "C003",
        "product_id": "P003",
        "status": "processing",
        "amount": 24.99,
        "expected_delivery": "2024-01-25",
        "carrier": "USPS",
        "tracking": None,
        "items": ["Phone Case"],
    },
    "999": {
        "order_id": "999",
        "customer_id": "C001",
        "product_id": "P004",
        "status": "delivered",
        "amount": 299.99,
        "expected_delivery": "2024-01-10",
        "carrier": "DHL",
        "tracking": "DH111222333",
        "items": ["Smart Watch"],
    },
}

CUSTOMERS = {
    "C001": {
        "customer_id": "C001",
        "name": "Priya Sharma",
        "email": "priya@example.com",
        "tier": "gold",
        "total_orders": 12,
        "refunds_issued": 1,
        "account_age_days": 730,
    },
    "C002": {
        "customer_id": "C002",
        "name": "Rahul Mehta",
        "email": "rahul@example.com",
        "tier": "silver",
        "total_orders": 5,
        "refunds_issued": 0,
        "account_age_days": 365,
    },
    "C003": {
        "customer_id": "C003",
        "name": "Anjali Patel",
        "email": "anjali@example.com",
        "tier": "bronze",
        "total_orders": 2,
        "refunds_issued": 0,
        "account_age_days": 90,
    },
}

PRODUCTS = {
    "P001": {
        "product_id": "P001",
        "name": "Blue Sneakers",
        "category": "Footwear",
        "return_window_days": 30,
        "warranty_days": 365,
        "in_stock": True,
    },
    "P002": {
        "product_id": "P002",
        "name": "Wireless Headphones",
        "category": "Electronics",
        "return_window_days": 15,
        "warranty_days": 730,
        "in_stock": True,
    },
    "P003": {
        "product_id": "P003",
        "name": "Phone Case",
        "category": "Accessories",
        "return_window_days": 30,
        "warranty_days": 90,
        "in_stock": False,
    },
    "P004": {
        "product_id": "P004",
        "name": "Smart Watch",
        "category": "Electronics",
        "return_window_days": 15,
        "warranty_days": 730,
        "in_stock": True,
    },
}

KNOWLEDGE_BASE = {
    "refund_policy": (
        "Customers can request refunds within 30 days of delivery for most items. "
        "Electronics have a 15-day return window. Refunds are processed within 5-7 business days."
    ),
    "delivery_delays": (
        "Orders may be delayed due to high demand or carrier issues. "
        "Delayed orders qualify for a 10% discount on next purchase."
    ),
    "damaged_product": (
        "If a product arrives damaged, the customer is eligible for a full refund or replacement. "
        "Photos of damage may be requested."
    ),
    "address_change": (
        "Address can be changed only if the order is in 'processing' status. "
        "Once shipped, address cannot be modified."
    ),
    "cancellation": (
        "Orders can be cancelled only if status is 'processing'. "
        "Shipped or delivered orders must go through the refund process."
    ),
}
