import unittest
from unittest.mock import MagicMock
from queue_manager import QueueManager


class TestQueueManagerCoverage(unittest.TestCase):
    def setUp(self):
        self.qm = QueueManager()

    def test_get_item_by_index_out_of_bounds(self):
        self.assertIsNone(self.qm.get_item_by_index(-1))
        self.assertIsNone(self.qm.get_item_by_index(100))

    def test_remove_listener_safe(self):
        # Remove a listener that isn't there
        func = MagicMock()
        self.qm.remove_listener(func)
        # Should not raise

        self.qm.add_listener(func)
        self.qm.remove_listener(func)
        self.assertEqual(len(self.qm._listeners), 0)

    def test_notify_listeners_exception(self):
        # Listener raising exception shouldn't crash
        bad_listener = MagicMock(side_effect=Exception("oops"))
        self.qm.add_listener(bad_listener)
        self.qm.add_item({"status": "Queued"})
        bad_listener.assert_called()

    def test_remove_item_not_found(self):
        item = {"status": "Queued"}
        self.qm.remove_item(item)  # Should not crash

    def test_swap_items_out_of_bounds(self):
        self.qm.add_item({"status": "A"})
        self.qm.add_item({"status": "B"})

        # Invalid indices
        self.qm.swap_items(0, 100)
        self.assertEqual(self.qm.get_all()[0]["status"], "A")

        self.qm.swap_items(-1, 0)
        self.assertEqual(self.qm.get_all()[0]["status"], "A")

    def test_claim_next_downloadable_none(self):
        # Empty queue
        self.assertIsNone(self.qm.claim_next_downloadable())

        # Queue with no "Queued" items
        self.qm.add_item({"status": "Downloading"})
        self.assertIsNone(self.qm.claim_next_downloadable())

    def test_any_in_status(self):
        self.qm.add_item({"status": "Test"})
        self.assertTrue(self.qm.any_in_status("Test"))
        self.assertFalse(self.qm.any_in_status("Other"))

    def test_any_downloading(self):
        self.assertFalse(self.qm.any_downloading())
        self.qm.add_item({"status": "Downloading"})
        self.assertTrue(self.qm.any_downloading())

    def test_any_downloading_allocating(self):
        self.qm.add_item({"status": "Allocating"})
        self.assertTrue(self.qm.any_downloading())

    def test_any_downloading_processing(self):
        self.qm.add_item({"status": "Processing"})
        self.assertTrue(self.qm.any_downloading())

    def test_max_queue_size(self):
        # Mock max size to be small for test
        self.qm.MAX_QUEUE_SIZE = 2
        self.qm.add_item({"status": "1"})
        self.qm.add_item({"status": "2"})
        with self.assertRaises(ValueError):
            self.qm.add_item({"status": "3"})
