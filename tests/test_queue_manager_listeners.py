import unittest
from unittest.mock import MagicMock

from queue_manager import QueueManager


class TestQueueManagerListeners(unittest.TestCase):

    def test_add_remove_listener(self):
        qm = QueueManager()
        listener = MagicMock()

        qm.add_listener(listener)
        qm.add_item({"id": 1})
        listener.assert_called_once()

        listener.reset_mock()
        qm.remove_listener(listener)
        qm.add_item({"id": 2})
        listener.assert_not_called()

    def test_listener_on_remove(self):
        qm = QueueManager()
        listener = MagicMock()
        qm.add_listener(listener)

        item = {"id": 1}
        qm.add_item(item)
        listener.reset_mock()

        qm.remove_item(item)
        listener.assert_called_once()

    def test_listener_on_swap(self):
        qm = QueueManager()
        listener = MagicMock()
        qm.add_listener(listener)

        qm.add_item({"id": 1})
        qm.add_item({"id": 2})
        listener.reset_mock()

        qm.swap_items(0, 1)
        listener.assert_called_once()

    def test_listener_not_called_on_invalid_op(self):
        qm = QueueManager()
        listener = MagicMock()
        qm.add_listener(listener)

        qm.remove_item({"id": 999})  # Not in queue
        listener.assert_not_called()

        qm.swap_items(0, 5)  # Invalid index
        listener.assert_not_called()
