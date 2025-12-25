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

from app_state import AppState, state
from downloader.types import DownloadOptions
from history_manager import HistoryManager
from queue_manager import QueueManager
from tasks import process_queue


class TestPipelineIntegration(unittest.TestCase):

    def setUp(self):
        # Reset state
        # We need a clean queue for each test
        state.queue_manager = QueueManager()
        state.current_download_item = None
        state.shutdown_flag.clear()

        # Ensure we don't have residual threads from other tests
        # We can't easily kill threads, but we can ensure shutdown flag is clear.

        # Patch tasks._submission_throttle (was _active_downloads) to avoid interference
        # We use the new name but patch legacy alias is also possible if tasks.py still uses it.
        # tasks.py aliases _active_downloads = _submission_throttle, so patching _submission_throttle is correct.
        self.patcher_sem = patch("tasks._submission_throttle", threading.Semaphore(3))
        self.patcher_sem.start()

    def tearDown(self):
        self.patcher_sem.stop()
        state.shutdown_flag.set()

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
        time.sleep(1.5)

        # 3. Verify execution
        mock_download.assert_called_once()

        # Tasks calls download_video with DownloadOptions object
        call_args = mock_download.call_args[0][0]
        self.assertIsInstance(call_args, DownloadOptions)
        self.assertEqual(call_args.url, "http://test.com/vid")

        # 4. Verify History Log
        # download_task calls _log_to_history on success
        # Wait for thread to finish? mock_download returns immediately (mock), so thread should finish fast.
        time.sleep(0.5)

        # NOTE: mock_download return value is default MagicMock, so info.get("filename") might be weird.
        # But logging happens.
        mock_add_history.assert_called()

    def test_pipeline_error_handling(self):
        """Test that errors in download are caught and status updated."""
        with patch("tasks.download_video", side_effect=Exception("Download Failed")):
            item = {"url": "http://fail.com", "status": "Queued", "title": "Fail Video"}
            state.queue_manager.add_item(item)

            process_queue()
            time.sleep(1.5)

            # Check status
            q_items = state.queue_manager.get_all()
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
            # 1. Update schedule (normally main loop does this)
            state.queue_manager.update_scheduled_items(datetime.datetime.now())

            # 2. Process
            process_queue()
            time.sleep(1.5)

            mock_dl.assert_called()
