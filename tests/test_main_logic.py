import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import ANY, MagicMock, patch

import tasks
from app_state import AppState
from tasks import download_task, process_queue
from tasks_extended import fetch_info_task
from utils import CancelToken
from queue_manager import QueueManager
from downloader.types import DownloadOptions


class TestMainLogic(unittest.TestCase):

    def setUp(self):
        # Reset singleton state
        self.mock_state = MagicMock()

        # Use real QueueManager for easier testing of queue logic
        self.mock_state.queue_manager = QueueManager()
        self.mock_state.current_download_item = None
        self.mock_state.shutdown_flag.is_set.return_value = False

        # Patch the global state in tasks and main
        self.patcher_main = patch("tasks_extended.state", self.mock_state)
        self.patcher_tasks = patch("app_state.state", self.mock_state)

        # Also patch tasks.state directly because tasks.py imports state
        self.patcher_tasks_direct = patch("tasks.state", self.mock_state)

        # Patch executor
        self.patcher_executor = patch("tasks._executor")

        # Patch active_downloads semaphore mock
        self.patcher_sem = patch("tasks._active_downloads", create=True)

        self.patcher_lock = patch("tasks._process_queue_lock", threading.RLock(), create=True)

        self.patcher_main.start()
        self.patcher_tasks.start()
        self.patcher_tasks_direct.start()
        self.mock_executor = self.patcher_executor.start()
        self.mock_sem = self.patcher_sem.start()
        self.patcher_lock.start()

        # Default semaphore behavior: acquire returns True
        self.mock_sem.acquire.return_value = True

    def tearDown(self):
        self.patcher_main.stop()
        self.patcher_tasks.stop()
        self.patcher_tasks_direct.stop()
        self.patcher_executor.stop()
        self.patcher_sem.stop()
        self.patcher_lock.stop()

    # --- CancelToken Tests ---
    def test_cancel_token(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        self.assertFalse(token.is_paused)

        token.cancel()
        self.assertTrue(token.cancelled)

        with self.assertRaisesRegex(Exception, "Download Cancelled by user"):
            token.check()

    def test_cancel_token_pause_resume(self):
        token = CancelToken()
        token.pause()
        self.assertTrue(token.is_paused)
        token.resume()
        self.assertFalse(token.is_paused)

    @patch("time.sleep")
    def test_cancel_token_check_while_paused(self, mock_sleep):
        token = CancelToken()
        token.pause()

        # We need to break the infinite loop in check
        # We can make sleep throw an exception or side effect on paused
        def side_effect(sec):
            token.resume()  # Stop pausing after one sleep

        mock_sleep.side_effect = side_effect

        token.check()
        mock_sleep.assert_called_once()

    # --- Process Queue Tests ---

    @patch("tasks.download_task")
    def test_process_queue_starts_download(self, mock_download_task):
        item = {"url": "http://test", "status": "Queued", "title": "T1"}
        self.mock_state.queue_manager.add_item(item)

        process_queue()

        # Check executor submit called
        self.mock_executor.submit.assert_called_once()
        args, kwargs = self.mock_executor.submit.call_args
        # First arg is function, second is item
        # But wait, we submit _wrapped_download_task
        # tasks._wrapped_download_task

        # Check args passed to submit
        # args[0] is the function, args[1] is the item
        submitted_item = args[1]
        self.assertEqual(submitted_item["url"], "http://test")

    def test_process_queue_scheduled(self):
        future_time = datetime.now() + timedelta(hours=1)
        item = {
            "url": "http://test",
            "status": "Scheduled (future)",
            "scheduled_time": future_time,
            "title": "Scheduled Item"
        }
        self.mock_state.queue_manager.add_item(item)

        process_queue()
        # Should still be scheduled (not picked up)
        q_items = self.mock_state.queue_manager.get_all()
        self.assertTrue(str(q_items[0]["status"]).startswith("Scheduled"))

        # Update time to past
        past_time = datetime.now() - timedelta(hours=1)
        q_items[0]["scheduled_time"] = past_time

        # Manually trigger schedule update
        self.mock_state.queue_manager.update_scheduled_items(datetime.now())

        process_queue()

        # Check if item status updated
        q_items_after = self.mock_state.queue_manager.get_all()
        # Should have been picked up -> Allocating or similar (managed by queue_manager claiming)
        # process_queue calls claim_next_downloadable which sets Allocating.
        # Then calls submit.
        self.assertFalse(str(q_items_after[0]["status"]).startswith("Scheduled"))

    def test_process_queue_busy(self):
        # Simulate busy by making semaphore acquire return False
        self.mock_sem.acquire.return_value = False

        item = {"url": "http://test", "status": "Queued", "title": "Busy Test"}
        self.mock_state.queue_manager.add_item(item)

        process_queue()

        # Should NOT submit
        self.mock_executor.submit.assert_not_called()

        # Should NOT claim item (remain Queued)
        q_items = self.mock_state.queue_manager.get_all()
        self.assertEqual(q_items[0]["status"], "Queued")

    # --- Download Task Tests ---

    @patch("tasks.download_video")
    @patch("history_manager.HistoryManager")
    @patch("tasks.process_queue")
    def test_download_task_success(
        self, mock_process_queue, MockHistory, mock_download_video
    ):
        # Configure download_video return value
        mock_download_video.return_value = {"filename": "video.mp4", "filepath": "/tmp/video.mp4"}

        item = {
            "url": "http://test",
            "status": "Queued",
            "control": MagicMock(),
            "output_path": ".",
        }

        download_task(item)

        self.assertEqual(item["status"], "Completed")
        mock_download_video.assert_called_once()

        # Check args to download_video (DownloadOptions)
        call_args = mock_download_video.call_args[0][0]
        self.assertIsInstance(call_args, DownloadOptions)
        self.assertEqual(call_args.url, "http://test")

        MockHistory.add_entry.assert_called_once()

    @patch("tasks.download_video")
    @patch("tasks.process_queue")
    def test_download_task_cancelled(
        self, mock_process_queue, mock_download_video
    ):
        item = {"url": "http://test", "status": "Queued"}
        mock_download_video.side_effect = Exception("Download Cancelled by user") # Matches tasks.py check string

        download_task(item)

        self.assertEqual(item["status"], "Cancelled")

    @patch("tasks.download_video")
    @patch("tasks.process_queue")
    def test_download_task_error(
        self, mock_process_queue, mock_download_video
    ):
        item = {"url": "http://test", "status": "Queued"}
        mock_download_video.side_effect = Exception("Network Error")

        download_task(item)

        self.assertEqual(item["status"], "Error")

    @patch("tasks.download_video")
    @patch("tasks.process_queue") # Need to patch this to avoid spawning threads in loop
    def test_download_task_progress_hook(self, mock_process_queue, mock_download_video):
        item = {"url": "http://test", "control": MagicMock()}

        # FIX: Add item to queue manager first so update_item_status works correctly
        self.mock_state.queue_manager.add_item(item)
        item_id = item["id"]

        # Configure return value
        mock_download_video.return_value = {"filename": "video.mp4"}

        def side_effect(options): # Changed signature to accept options
            hook = options.progress_hook

            # Simulate downloading
            d = {
                "status": "downloading",
                "_percent_str": "50%",
                "_speed_str": "1MB/s",
                "_eta_str": "10s",
                "_total_bytes_str": "100MB",
            }
            hook(d)
            # Simulate finished
            d_finished = {"status": "finished", "filename": "video.mp4"}
            hook(d_finished)

            return {"filename": "video.mp4"}

        mock_download_video.side_effect = side_effect

        download_task(item)

        # After download_video returns, it sets status to "Completed"
        self.assertEqual(item["status"], "Completed")

        # Check intermediate calls
        self.assertTrue(item["control"].update_progress.call_count >= 2)

        # Verify queue manager content
        q_item = self.mock_state.queue_manager.get_item_by_id(item_id)
        if q_item:
             self.assertEqual(q_item.get("filename"), "video.mp4")

    # --- Fetch Info Task Tests ---

    @patch("tasks_extended.get_video_info")
    def test_fetch_info_task_success(self, mock_get_info):
        mock_get_info.return_value = {"title": "Test Video"}
        mock_view = MagicMock()
        mock_page = MagicMock()

        fetch_info_task("http://video", mock_view, mock_page)

        self.assertEqual(self.mock_state.video_info["title"], "Test Video")
        mock_view.update_info.assert_called()
        mock_page.open.assert_called()

    @patch("tasks_extended.get_video_info")
    def test_fetch_info_task_failure(self, mock_get_info):
        mock_get_info.return_value = None
        mock_view = MagicMock()
        mock_page = MagicMock()

        fetch_info_task("http://video", mock_view, mock_page)

        # Should raise exception and log error
        mock_page.open.assert_called()  # SnackBar
