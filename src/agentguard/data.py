from .models import Task

ORDERS = {
    "A1001": {"status": "delivered", "refund": "processing", "item": "headphones"},
    "A1002": {"status": "in_transit", "refund": None, "item": "keyboard"},
}
POLICIES = {
    "refund_timeline": "Refunds usually arrive 3-5 business days after delivery is confirmed.",
    "return_opened": "Opened items may be returned within 7 days when they remain suitable for resale.",
}
DELIVERY = {"A1002": "Expected delivery is within 2 days."}

TASKS = (
    Task("refund_001", "Order A1001 is delivered. When will I receive my refund?", ("query_order", "search_policy"), {"query_order": {"order_id": "A1001"}}, ("3-5",), True),
    Task("order_001", "What is the status of order A1001?", ("query_order",), {"query_order": {"order_id": "A1001"}}, ("delivered",)),
    Task("delivery_001", "When will order A1002 arrive?", ("query_order", "estimate_delivery"), {"query_order": {"order_id": "A1002"}, "estimate_delivery": {"order_id": "A1002"}}, ("2 days",)),
    Task("policy_001", "Can I return an opened product?", ("search_policy",), {}, ("7 days",)),
    Task("ticket_001", "My item is damaged and previous conversations did not resolve it. Please transfer me to a person.", ("create_ticket",), {}, ("ticket",), True),
    Task("refund_002", "What is the refund status for the headphones in A1001?", ("query_order",), {"query_order": {"order_id": "A1001"}}, ("processing",)),
)
