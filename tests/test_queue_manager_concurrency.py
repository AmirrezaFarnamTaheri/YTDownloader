import unittest
import threading
import sys
import os

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from queue_manager import QueueManager

class TestQueueManagerConcurrency(unittest.TestCase):
    def setUp(self):
        self.qm = QueueManager()

    def test_claim_next_downloadable_atomic(self):
        # Add multiple queued items
        for i in range(10):
            self.qm.add_item({'id': i, 'status': 'Queued'})

        claimed_items = []
        lock = threading.Lock()

        def worker():
            while True:
                item = self.qm.claim_next_downloadable()
                if item:
                    with lock:
                        claimed_items.append(item)
                else:
                    break

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have claimed all 10 items exactly once
        self.assertEqual(len(claimed_items), 10)

        # Check IDs are unique (no double claims)
        ids = [item['id'] for item in claimed_items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_any_downloading_includes_allocating(self):
        self.qm.add_item({'status': 'Allocating'})
        self.assertTrue(self.qm.any_downloading())

    def test_any_downloading_includes_processing(self):
        self.qm.add_item({'status': 'Processing'})
        self.assertTrue(self.qm.any_downloading())

if __name__ == '__main__':
    unittest.main()
