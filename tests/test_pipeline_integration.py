# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
# pylint: disable=duplicate-code
"""
Integration tests for the entire pipeline.
Simulates adding to queue -> processing -> downloading -> history.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import tasks  # Import module to ensure dynamic lookup
from app_state import state
from downloader.types import DownloadOptions
from queue_manager import QueueManager


class TestPipelineIntegration(unittest.TestCase):

    def setUp(self):
        # Reset state
        # We need a clean queue for each test
        state.queue_manager = QueueManager()
        state.current_download_item = None
        state.shutdown_flag.clear()

        # Force re-creation of executor in tasks.py by clearing global
        with tasks._executor_lock:
            if tasks._executor:
                tasks._executor.shutdown(wait=False)
                tasks._executor = None

        # Patch tasks._SUBMISSION_THROTTLE to avoid interference
        # We replace the semaphore in the module with a fresh one
        self.patcher_sem = patch("tasks._SUBMISSION_THROTTLE", threading.Semaphore(3))
        self.mock_sem = self.patcher_sem.start()

    def tearDown(self):
        self.patcher_sem.stop()
        state.shutdown_flag.set()
        # Clean up executor
        with tasks._executor_lock:
            if tasks._executor:
                tasks._executor.shutdown(wait=False)
                tasks._executor = None

    @patch("tasks.download_video")
    @patch("history_manager.HistoryManager.add_entry")
    def test_pipeline_flow_success(self, mock_add_history, mock_download):
        """
        Test the full pipeline from adding an item to completion.
        We mock the actual download_video call.
        """
        # Configure mock to return valid result
        mock_download.return_value = {"filename": "vid.mp4", "filepath": "/tmp/vid.mp4"}

        # 1. Add item
        item = {
            "url": "http://test.com/vid",
            "status": "Queued",
            "title": "Test Video",
            "video_format": "best",
            "output_path": "/tmp",
        }
        state.queue_manager.add_item(item)

        # 2. Trigger processing using module reference
        tasks.process_queue(None)

        # Since process_queue spawns a thread via executor, we need to wait briefly
        # The thread executes `_wrapped_download_task` -> `download_task` -> `download_video`
        # Increase sleep slightly to be safe
        time.sleep(2.5)

        # 3. Verify execution
        if mock_download.call_count == 0:
            # Debugging info
            print(f"\nDEBUG: Queue Items: {state.queue_manager.get_all()}")
            self.fail("download_video was not called.")

        mock_download.assert_called_once()

        # Tasks calls download_video with DownloadOptions object
        call_args = mock_download.call_args[0][0]
        self.assertIsInstance(call_args, DownloadOptions)
        self.assertEqual(call_args.url, "http://test.com/vid")

        # 4. Verify History Log
        mock_add_history.assert_called()

    def test_pipeline_error_handling(self):
        """Test that errors in download are caught and status updated."""
        with patch("tasks.download_video", side_effect=Exception("Download Failed")):
            item = {"url": "http://fail.com", "status": "Queued", "title": "Fail Video"}
            state.queue_manager.add_item(item)

            tasks.process_queue(None)
            time.sleep(2.5)

            # Check status
            q_items = state.queue_manager.get_all()
            if not q_items:
                self.fail("Queue item missing")

            self.assertEqual(q_items[0]["status"], "Error")
            self.assertEqual(q_items[0].get("error"), "Download Failed")

    def test_scheduling_execution(self):
        """Test that scheduled items are picked up."""
        # Use real time logic
        import datetime

        now = datetime.datetime.now()
        past = now - datetime.timedelta(minutes=1)

        item = {
            "url": "http://sched.com",
            "status": f"Scheduled ({past.strftime('%H:%M')})",
            "scheduled_time": past,
            "title": "Sched Video",
        }
        state.queue_manager.add_item(item)

        # Mock download to verify it ran
        with patch("tasks.download_video") as mock_dl:
            mock_dl.return_value = {}

            # 1. Update schedule (normally main loop does this)
            state.queue_manager.update_scheduled_items(datetime.datetime.now())

            # 2. Process
            tasks.process_queue(None)
            time.sleep(2.5)

            mock_dl.assert_called()
