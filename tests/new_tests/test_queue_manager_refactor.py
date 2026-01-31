"""
Tests for QueueManager refactored with DownloadStatus Enum.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock

from downloader.types import DownloadStatus
from queue_manager import QueueManager


class TestQueueManagerRefactor(unittest.TestCase):
    def setUp(self):
        self.qm = QueueManager()

    def test_add_item_enum_status(self):
        item = {"url": "http://example.com", "title": "Test"}
        self.qm.add_item(item)

        q_item = self.qm.get_item_by_index(0)
        # Default should be Queued (string) or Enum?
        # QueueManager code: if "status" not in item: item["status"] = "Queued"
        # Ideally it should be DownloadStatus.QUEUED
        # But for backward compat it might use string.
        # Let's check what it sets.
        self.assertEqual(q_item["status"], "Queued") # Current implementation defaults to string "Queued"

    def test_update_status_enum(self):
        item = {"url": "http://example.com", "title": "Test", "status": DownloadStatus.QUEUED}
        self.qm.add_item(item)
        item_id = self.qm.get_item_by_index(0)["id"]

        self.qm.update_item_status(item_id, DownloadStatus.DOWNLOADING)

        updated = self.qm.get_item_by_id(item_id)
        self.assertEqual(updated["status"], DownloadStatus.DOWNLOADING)
        self.assertEqual(str(updated["status"]), "Downloading")

    def test_scheduled_status(self):
        item = {
            "url": "http://example.com",
            "status": DownloadStatus.SCHEDULED,
            "scheduled_time": "future" # Mock
        }
        self.qm.add_item(item)
        q_item = self.qm.get_item_by_index(0)
        self.assertEqual(q_item["status"], DownloadStatus.SCHEDULED)

    def test_claim_next(self):
        item1 = {"url": "1", "status": DownloadStatus.QUEUED}
        item2 = {"url": "2", "status": DownloadStatus.PAUSED}
        self.qm.add_item(item1)
        self.qm.add_item(item2)

        claimed = self.qm.claim_next_downloadable()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["url"], "1")
        self.assertEqual(claimed["status"], "Allocating") # claim_next sets "Allocating" (string)

        claimed2 = self.qm.claim_next_downloadable()
        self.assertIsNone(claimed2)

if __name__ == "__main__":
    unittest.main()
