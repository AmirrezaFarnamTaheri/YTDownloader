import pytest
from unittest.mock import MagicMock
from queue_manager import QueueManager


def test_add_listener_duplicate():
    """Test that adding the same listener twice doesn't duplicate it."""
    qm = QueueManager()
    listener = MagicMock()
    qm.add_listener(listener)
    qm.add_listener(listener)

    # Manually inspect internal list (white-box) or check notification count
    # White-box testing for coverage
    assert len(qm._listeners) == 1


def test_notify_listeners_error():
    """Test exception handling within notify listeners."""
    qm = QueueManager()

    def bad_listener():
        raise Exception("Boom")

    qm.add_listener(bad_listener)

    # Should not raise
    qm._notify_listeners_safe()


def test_remove_item_not_found():
    """Test removing an item that isn't in the queue."""
    qm = QueueManager()
    item = {"status": "Queued"}
    qm.remove_item(item)  # Should do nothing
    assert len(qm.get_all()) == 0


def test_swap_items_out_of_bounds():
    """Test swapping with invalid indices."""
    qm = QueueManager()
    qm.add_item({"id": 1})
    qm.add_item({"id": 2})

    qm.swap_items(0, 5)  # Invalid
    assert qm.get_item_by_index(0)["id"] == 1

    qm.swap_items(-1, 0)  # Invalid
    assert qm.get_item_by_index(0)["id"] == 1
