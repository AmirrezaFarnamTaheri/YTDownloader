import unittest
import time
import threading
from unittest.mock import MagicMock
from utils import CancelToken
from queue_manager import QueueManager


class TestCancelToken(unittest.TestCase):
    def test_cancel(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        token.cancel()
        self.assertTrue(token.cancelled)

    def test_check_raises(self):
        token = CancelToken()
        token.cancel()
        with self.assertRaises(Exception) as cm:
            token.check()
        self.assertIn("cancelled", str(cm.exception))

    def test_pause_resume(self):
        token = CancelToken()
        token.pause()
        self.assertTrue(token.is_paused)

        # We can't easily test the loop inside check() without threading or mocking time.sleep
        # But we can verify resume() unsets the flag
        token.resume()
        self.assertFalse(token.is_paused)


class TestQueueManagerConcurrency(unittest.TestCase):
    def test_claim_next_downloadable(self):
        qm = QueueManager()
        # Add multiple items
        for i in range(10):
            qm.add_item({"id": i, "status": "Queued"})

        claimed_items = []

        def worker():
            while True:
                item = qm.claim_next_downloadable()
                if item:
                    claimed_items.append(item["id"])
                else:
                    break

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Ensure all items were claimed exactly once
        self.assertEqual(len(claimed_items), 10)
        self.assertEqual(len(set(claimed_items)), 10)

    def test_listeners_thread_safety(self):
        qm = QueueManager()

        def listener():
            pass

        def adder():
            for _ in range(100):
                qm.add_listener(listener)

        def remover():
            for _ in range(100):
                qm.remove_listener(listener)

        t1 = threading.Thread(target=adder)
        t2 = threading.Thread(target=remover)

        t1.start()
        t2.start()

        t1.join()
        t2.join()
        # Should not crash


if __name__ == "__main__":
    unittest.main()
