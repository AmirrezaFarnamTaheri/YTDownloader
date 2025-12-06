# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import os
import sys
import threading
import unittest

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from queue_manager import QueueManager


class TestQueueManagerBasic(unittest.TestCase):
    def setUp(self):
        self.qm = QueueManager()

    def test_add_remove_item(self):
        item = {"url": "http://test", "status": "Queued"}
        self.qm.add_item(item)
        self.assertEqual(len(self.qm.get_all()), 1)

        self.qm.remove_item(item)
        self.assertEqual(len(self.qm.get_all()), 0)

    def test_swap_items(self):
        item1 = {"url": "1", "status": "Queued"}
        item2 = {"url": "2", "status": "Queued"}
        self.qm.add_item(item1)
        self.qm.add_item(item2)

        self.qm.swap_items(0, 1)
        items = self.qm.get_all()
        self.assertEqual(items[0], item2)
        self.assertEqual(items[1], item1)

    def test_threading_lock(self):
        # Basic race condition check for standard add (not claim)
        threads = []
        for i in range(100):
            t = threading.Thread(
                target=self.qm.add_item, args=({"id": i, "status": "Queued"},)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(self.qm.get_all()), 100)


if __name__ == "__main__":
    unittest.main()
