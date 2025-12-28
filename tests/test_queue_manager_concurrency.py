# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import threading
import time
import unittest

from queue_manager import QueueManager


class TestQueueManagerConcurrency(unittest.TestCase):
    def setUp(self):
        self.qm = QueueManager()

    def test_claim_next_downloadable_race_condition(self):
        """
        Test that multiple threads attempting to claim items do not claim the same item.
        """
        # Add multiple items
        for i in range(10):
            self.qm.add_item({"id": i, "status": "Queued", "url": f"http://test/{i}"})

        claimed_items = []
        lock = threading.Lock()

        def worker():
            while True:
                item = self.qm.claim_next_downloadable()
                if item is None:
                    break
                with lock:
                    claimed_items.append(item)
                # Simulate some work time to allow context switching
                time.sleep(0.01)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify each item was claimed exactly once
        claimed_ids = [item["id"] for item in claimed_items]
        self.assertEqual(len(claimed_ids), 10)
        self.assertEqual(len(set(claimed_ids)), 10)

    def test_add_item_thread_safety(self):
        """Test adding items from multiple threads."""

        def worker(start, count):
            for i in range(count):
                self.qm.add_item({"id": start + i, "status": "Queued"})

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i * 100, 100))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(self.qm.get_all()), 400)


if __name__ == "__main__":
    unittest.main()
