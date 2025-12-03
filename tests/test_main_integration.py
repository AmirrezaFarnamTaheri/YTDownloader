"""
Integration tests for main application logic.
"""

import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import tasks
from app_state import AppState
from queue_manager import QueueManager
from tasks import download_task, process_queue


class TestMainIntegration(unittest.TestCase):

    def setUp(self):
        # Reset singleton state
        self.state = AppState()
        self.state.queue_manager = QueueManager()
        self.state.current_download_item = None
        # Mock shutdown_flag if it's an Event
        self.state.shutdown_flag = MagicMock()
        self.state.shutdown_flag.is_set.return_value = False

        # Patch active_downloads to avoid thread pool execution if needed
        # Or patch executor.submit
        self.patcher_executor = patch("tasks.EXECUTOR")
        self.mock_executor = self.patcher_executor.start()

        # We need to make sure process_queue submits
        self.patcher_sem = patch("tasks._SUBMISSION_THROTTLE", create=True)
        self.mock_sem = self.patcher_sem.start()
        self.mock_sem.acquire.return_value = True

        self.patcher_lock = patch(
            "tasks._PROCESS_QUEUE_LOCK", threading.RLock(), create=True
        )
        self.patcher_lock.start()

    def tearDown(self):
        self.patcher_executor.stop()
        self.patcher_sem.stop()
        self.patcher_lock.stop()

    @patch("tasks.download_task")
    @patch("tasks.download_video")
    @patch("tasks._log_to_history")
    def test_download_task_success(self, mock_history, mock_download, mock_dl_task):
        item = {"url": "http://test", "status": "Queued", "title": "Test Video"}
        mock_download.return_value = {"filename": "vid.mp4", "filepath": "/tmp/vid.mp4"}

        # Patch state in tasks module so it sees our mock state/queue manager
        with patch("tasks.state", self.state):
            download_task(item)

        self.assertEqual(item["status"], "Completed")
        mock_download.assert_called_once()
        mock_history.assert_called_once()

    @patch("tasks.download_video")
    def test_download_task_failure(self, mock_download):
        item = {"url": "http://test", "status": "Queued"}
        mock_download.side_effect = Exception("Failed")

        # Add to queue
        self.state.queue_manager.add_item(item)
        item_id = item["id"]

        with patch("tasks.state", self.state):
            download_task(item)

        # Check queue item
        q_item = self.state.queue_manager.get_item_by_id(item_id)
        if q_item:
            self.assertEqual(q_item["status"], "Error")
            self.assertIn("Failed", q_item["error"])

    @patch("tasks.download_task")
    def test_process_queue_scheduler(self, mock_download_task):
        future_time = datetime.now() + timedelta(minutes=10)
        item = {
            "url": "http://sched.com",
            "status": "Scheduled (12:00)",
            "scheduled_time": future_time,
        }
        self.state.queue_manager.add_item(item)

        # Patch state in tasks module!
        with patch("tasks.state", self.state):
            process_queue()

            # Should still be scheduled
            self.mock_executor.submit.assert_not_called()

            # Move time to past
            item["scheduled_time"] = datetime.now() - timedelta(minutes=1)

            # Manually trigger schedule update
            self.state.queue_manager.update_scheduled_items(datetime.now())

            process_queue()

        # Should be submitted
        self.mock_executor.submit.assert_called()
