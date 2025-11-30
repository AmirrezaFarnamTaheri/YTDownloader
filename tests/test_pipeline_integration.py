import threading
import time
import unittest
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import tasks
import main  # Import main to access potential background threads logic if needed
from app_state import state
from queue_manager import QueueManager
from tasks import download_task, process_queue

logger = logging.getLogger(__name__)

class TestPipelineIntegration(unittest.TestCase):
    def setUp(self):
        # 1. Stop any lingering background threads from previous tests
        # We set the flag to TRUE to stop background loops.
        state.shutdown_flag.set()

        # Wait longer than the background loop's sleep interval (2s)
        # to ensure any sleeping threads wake up, check the flag, and exit.
        time.sleep(2.2)

        # Now it is safe to clear the flag, because all zombie loops should have exited.
        state.shutdown_flag.clear()

        # 2. Reset state
        state.queue_manager = QueueManager()
        state.current_download_item = None
        state.cancel_token = None
        state.config = {}

        # 3. Reset concurrency primitives
        tasks._active_downloads = threading.Semaphore(3)
        tasks._process_queue_lock = threading.RLock()

    @patch("tasks.download_video")
    @patch("history_manager.HistoryManager.add_entry")
    def test_pipeline_flow_success(self, mock_add_history, mock_download):
        """
        Test the full pipeline from adding an item to completion.
        We mock the actual download_video call.
        """
        # 1. Add item
        item = {
            "url": "http://test.com/vid",
            "status": "Queued",
            "title": "Test Video",
            "video_format": "best",
            "output_path": "/tmp",
        }
        state.queue_manager.add_item(item)

        # 2. Trigger processing (simulate what main.py background loop does)
        process_queue()

        # Since process_queue spawns a thread, we need to wait briefly
        time.sleep(0.5)

        # 3. Verify execution
        mock_download.assert_called_once()
        args, _ = mock_download.call_args
        self.assertEqual(args[0], "http://test.com/vid")

        # Verify item status
        q_items = state.queue_manager.get_all()
        self.assertEqual(len(q_items), 1)
        self.assertEqual(q_items[0]["status"], "Completed")

        # Verify history added
        mock_add_history.assert_called_once()

    @patch("tasks.download_video")
    def test_pipeline_error_handling(self, mock_download):
        """Test pipeline handles errors gracefully."""
        mock_download.side_effect = Exception("Network Error")

        item = {"url": "http://fail.com", "status": "Queued"}
        state.queue_manager.add_item(item)

        process_queue()
        time.sleep(0.5)

        q_items = state.queue_manager.get_all()
        self.assertEqual(q_items[0]["status"], "Error")

    def test_scheduling_logic(self):
        """Test that scheduled items are picked up only when time is right."""
        # Set scheduled time to future
        future_time = datetime.now() + timedelta(hours=1)
        item = {
            "url": "http://future.com",
            "status": f"Scheduled ({future_time.strftime('%H:%M')})",
            "scheduled_time": future_time,
        }
        state.queue_manager.add_item(item)

        process_queue()
        time.sleep(0.1)

        # Should still be scheduled
        q_items = state.queue_manager.get_all()
        self.assertTrue(str(q_items[0]["status"]).startswith("Scheduled"))

        # Now move time to past (simulate by modifying item time)
        item["scheduled_time"] = datetime.now() - timedelta(seconds=1)

        process_queue()
        time.sleep(0.1)

    @patch("tasks.download_video")
    def test_scheduling_execution(self, mock_download):
        now = datetime.now()
        past_time = now - timedelta(seconds=1)
        item = {
            "url": "http://now.com",
            "status": f"Scheduled ({past_time.strftime('%H:%M')})",
            "scheduled_time": past_time,
        }
        state.queue_manager.add_item(item)

        process_queue()
        time.sleep(0.5)

        # Should be processed
        mock_download.assert_called()


if __name__ == "__main__":
    unittest.main()
