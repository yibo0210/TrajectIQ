from trajectiq.data import DEFAULT_DATASET, TASKS


def test_packaged_dataset_has_a_stable_version_and_business_slices() -> None:
    assert DEFAULT_DATASET.identifier == "customer_support_v1"
    assert len(TASKS) == 36
    assert {task.category for task in TASKS} == {
        "delivery",
        "escalation",
        "order_status",
        "refund_status",
        "refund_timeline",
        "return_policy",
    }
    assert {task.task_id for task in TASKS if task.critical} == {
        "refund_001",
        "refund_003",
        "refund_009",
        "ticket_001",
    }
