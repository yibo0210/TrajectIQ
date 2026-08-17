"""Deterministic support fixtures and the packaged evaluation dataset."""

from .dataset import load_default_dataset

ORDERS = {
    "A1001": {"status": "delivered", "refund": "processing", "item": "headphones"},
    "A1002": {"status": "in_transit", "refund": None, "item": "keyboard"},
}
POLICIES = {
    "refund_timeline": "Refunds usually arrive 3-5 business days after delivery is confirmed.",
    "return_opened": "Opened items may be returned within 7 days when they remain suitable for resale.",
}
DELIVERY = {"A1002": "Expected delivery is within 2 days."}

DEFAULT_DATASET = load_default_dataset()
TASKS = DEFAULT_DATASET.tasks
