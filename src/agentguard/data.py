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

def _refund_timeline(task_id: str, text: str, critical: bool = False) -> Task:
    return Task(
        task_id,
        "refund_timeline",
        text,
        ("query_order", "search_policy"),
        {"query_order": {"order_id": "A1001"}},
        ("3-5",),
        critical,
    )


def _refund_status(task_id: str, text: str, critical: bool = False) -> Task:
    return Task(
        task_id,
        "refund_status",
        text,
        ("query_order",),
        {"query_order": {"order_id": "A1001"}},
        ("processing",),
        critical,
    )


def _order_status(task_id: str, text: str) -> Task:
    return Task(
        task_id,
        "order_status",
        text,
        ("query_order",),
        {"query_order": {"order_id": "A1001"}},
        ("delivered",),
    )


def _delivery(task_id: str, text: str) -> Task:
    return Task(
        task_id,
        "delivery",
        text,
        ("query_order", "estimate_delivery"),
        {"query_order": {"order_id": "A1002"}, "estimate_delivery": {"order_id": "A1002"}},
        ("2 days",),
    )


def _return_policy(task_id: str, text: str) -> Task:
    return Task(
        task_id,
        "return_policy",
        text,
        ("search_policy",),
        {},
        ("7 days",),
    )


def _escalation(task_id: str, text: str, critical: bool = False) -> Task:
    return Task(
        task_id,
        "escalation",
        text,
        ("create_ticket",),
        {},
        ("ticket",),
        critical,
    )


TASKS = (
    _refund_timeline("refund_001", "Order A1001 is delivered. When will I receive my refund?", True),
    _refund_timeline("refund_002", "When will the refund for A1001 arrive in my account?"),
    _refund_timeline("refund_003", "A1001 was delivered. When can I expect my refund?", True),
    _refund_timeline("refund_004", "When is the refund payment for order A1001 due?"),
    _refund_timeline("refund_005", "I returned A1001. When will my refund arrive?"),
    _refund_status("refund_006", "What is the refund status for the headphones in A1001?"),
    _refund_status("refund_007", "Show the refund progress for order A1001."),
    _refund_status("refund_008", "Is the refund for A1001 still processing?"),
    _refund_status("refund_009", "Check A1001 refund status for me.", True),
    _refund_status("refund_010", "Has the refund on order A1001 been started?"),
    _order_status("order_001", "What is the status of order A1001?"),
    _order_status("order_002", "Please check the current state of A1001."),
    _order_status("order_003", "Is order A1001 delivered?"),
    _order_status("order_004", "Give me the order details for A1001."),
    _order_status("order_005", "What happened to my A1001 order purchase?"),
    _order_status("order_006", "Look up order A1001."),
    _order_status("order_007", "I need the latest order status for A1001."),
    _order_status("order_008", "Can you verify whether A1001 was delivered?"),
    _delivery("delivery_001", "When will order A1002 arrive?"),
    _delivery("delivery_002", "Can you tell me when A1002 will arrive?"),
    _delivery("delivery_003", "My keyboard order A1002 has not arrived. When will it arrive?"),
    _delivery("delivery_004", "What is the expected arrival date for A1002?"),
    _delivery("delivery_005", "Please check when order A1002 will arrive."),
    _delivery("delivery_006", "When should I expect A1002 to arrive?"),
    _delivery("delivery_007", "Please confirm the arrival estimate for order A1002."),
    _return_policy("policy_001", "Can I return an opened product?"),
    _return_policy("policy_002", "Is a return allowed after opening an item?"),
    _return_policy("policy_003", "What is the return policy for an opened keyboard?"),
    _return_policy("policy_004", "Can a product be returned within seven days after opening?"),
    _return_policy("policy_005", "May I return merchandise that has been opened?"),
    _escalation("ticket_001", "My item is damaged and previous conversations did not resolve it. Please transfer me to a person.", True),
    _escalation("ticket_002", "Please transfer me to a person because my order issue is unresolved."),
    _escalation("ticket_003", "I need a person to review this damaged item."),
    _escalation("ticket_004", "Transfer this case to a support person."),
    _escalation("ticket_005", "Please create a ticket for a person to handle my issue."),
    _escalation("ticket_006", "A person needs to investigate this support request."),
)
