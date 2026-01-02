# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
# pylint: disable=duplicate-code
import threading
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from downloader.types import DownloadOptions
from queue_manager import QueueManager
from tasks import download_task, process_queue, fetch_info_task
from utils import CancelToken


class TestMainLogic(unittest.TestCase):

    def setUp(self):
        # Reset singleton state
        self.mock_state = MagicMock()

        # Use real QueueManager for easier testing of queue logic
        self.mock_state.queue_manager = QueueManager()
        self.mock_state.current_download_item = None
        self.mock_state.shutdown_flag.is_set.return_value = False

        # Patch the global state in app_state which tasks.py imports
        self.patcher_app_state = patch("app_state.state", self.mock_state)

        # Patch executor - NOW using _get_executor
        self.patcher_executor = patch("tasks._get_executor")
        self.mock_get_executor = self.patcher_executor.start()
        self.mock_executor = MagicMock()
        self.mock_get_executor.return_value = self.mock_executor

        # Patch submission throttle semaphore mock
        self.patcher_sem = patch("tasks._SUBMISSION_THROTTLE", create=True)

        self.patcher_lock = patch(
            "tasks._PROCESS_QUEUE_LOCK", threading.RLock(), create=True
        )

        self.patcher_app_state.start()
        self.mock_sem = self.patcher_sem.start()
        self.patcher_lock.start()

        # Default semaphore behavior: acquire returns True
        self.mock_sem.acquire.return_value = True

    def tearDown(self):
        self.patcher_app_state.stop()
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

        process_queue(None)

        # Check executor submit called
        self.mock_executor.submit.assert_called_once()
        args, kwargs = self.mock_executor.submit.call_args
        # First arg is function, second is item
        submitted_item = args[1]
        self.assertEqual(submitted_item["url"], "http://test")

    def test_process_queue_scheduled(self):
        future_time = datetime.now() + timedelta(hours=1)
        item = {
            "url": "http://test",
            "status": "Scheduled (future)",
            "scheduled_time": future_time,
            "title": "Scheduled Item",
        }
        self.mock_state.queue_manager.add_item(item)

        process_queue(None)
        # Should still be scheduled (not picked up)
        q_items = self.mock_state.queue_manager.get_all()
        self.assertTrue(str(q_items[0]["status"]).startswith("Scheduled"))

        # Update time to past
        past_time = datetime.now() - timedelta(hours=1)
        q_items[0]["scheduled_time"] = past_time

        # Manually trigger schedule update
        self.mock_state.queue_manager.update_scheduled_items(datetime.now())

        process_queue(None)

        # Check if item status updated
        q_items_after = self.mock_state.queue_manager.get_all()
        # Should have been picked up -> Allocating or similar (managed by queue_manager claiming)
        self.assertFalse(str(q_items_after[0]["status"]).startswith("Scheduled"))

    def test_process_queue_busy(self):
        # Simulate busy by making semaphore acquire return False
        self.mock_sem.acquire.return_value = False

        item = {"url": "http://test", "status": "Queued", "title": "Busy Test"}
        self.mock_state.queue_manager.add_item(item)

        process_queue(None)

        # Should NOT submit
        self.mock_executor.submit.assert_not_called()

        # Should NOT claim item (remain Queued)
        # Note: If acquire returns False, we return immediately without claiming.
        # So item status remains "Queued".
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
        mock_download_video.return_value = {
            "filename": "video.mp4",
            "filepath": "/tmp/video.mp4",
        }

        item = {
            "url": "http://test",
            "status": "Queued",
            "control": MagicMock(),
            "output_path": ".",
        }
        # Add to queue manager
        self.mock_state.queue_manager.add_item(item)

        download_task(item, None)

        self.assertEqual(item["status"], "Completed")
        mock_download_video.assert_called_once()

        # Check args to download_video (DownloadOptions)
        call_args = mock_download_video.call_args[0][0]
        self.assertIsInstance(call_args, DownloadOptions)
        self.assertEqual(call_args.url, "http://test")

        # tasks.py calls app_state.state.history_manager.add_entry
        self.mock_state.history_manager.add_entry.assert_called_once()

    @patch("tasks.download_video")
    @patch("tasks.process_queue")
    def test_download_task_cancelled(self, mock_process_queue, mock_download_video):
        item = {"url": "http://test", "status": "Queued"}
        self.mock_state.queue_manager.add_item(item)

        mock_download_video.side_effect = Exception(
            "Download Cancelled by user"
        )  # Matches tasks.py check string

        download_task(item, None)

        # Re-fetch item from queue manager to check status
        # Because local 'item' dict is not automatically updated if queue manager creates a copy
        # BUT download_task modifies 'item' passed to it?
        # download_task does: qm.update_item_status(item_id, ...)
        # It does NOT update 'item' dict passed as arg for status changes inside exception block?
        # Wait, 'download_task' doesn't modify 'item' dict for status. It calls qm.
        # EXCEPT at the beginning: qm.update_item_status(item_id, "Downloading").
        # So we should check QM.
        q_items = self.mock_state.queue_manager.get_all()
        self.assertEqual(q_items[0]["status"], "Cancelled")

    @patch("tasks.download_video")
    @patch("tasks.process_queue")
    def test_download_task_error(self, mock_process_queue, mock_download_video):
        item = {"url": "http://test", "status": "Queued"}
        self.mock_state.queue_manager.add_item(item)

        mock_download_video.side_effect = Exception("Network Error")

        download_task(item, None)

        q_items = self.mock_state.queue_manager.get_all()
        self.assertEqual(q_items[0]["status"], "Error")

    @patch("tasks.download_video")
    @patch(
        "tasks.process_queue"
    )  # Need to patch this to avoid spawning threads in loop
    def test_download_task_progress_hook(self, mock_process_queue, mock_download_video):
        item = {"url": "http://test", "control": MagicMock()}

        # FIX: Add item to queue manager first so update_item_status works correctly
        self.mock_state.queue_manager.add_item(item)
        item_id = item["id"]

        # Configure return value
        mock_download_video.return_value = {"filename": "video.mp4"}

        def side_effect(options):  # Changed signature to accept options
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

        download_task(item, None)

        # After download_video returns, it sets status to "Completed"
        q_items = self.mock_state.queue_manager.get_all()
        self.assertEqual(q_items[0]["status"], "Completed")

        # Check intermediate calls
        control_ref = item.get("control_ref")
        if control_ref:
            control = control_ref()
            if control:
                self.assertTrue(control.update_progress.call_count >= 2)

        # Verify queue manager content
        q_item = self.mock_state.queue_manager.get_item_by_id(item_id)
        if q_item:
            self.assertEqual(q_item.get("filename"), "video.mp4")

    # --- Fetch Info Task Tests ---

    @patch("tasks.get_video_info")
    def test_fetch_info_task_success(self, mock_get_info):
        mock_get_info.return_value = {"title": "Test Video"}
        mock_view = MagicMock()
        mock_page = MagicMock()

        # Simulate run_task executing the async callback
        import asyncio
        def run_task_side_effect(func, *args, **kwargs):
            res = func(*args, **kwargs)
            if asyncio.iscoroutine(res):
                asyncio.run(res)
            return res

        mock_page.run_task.side_effect = run_task_side_effect

        fetch_info_task("http://video", mock_view, mock_page)

        self.assertEqual(self.mock_state.video_info["title"], "Test Video")
        mock_view.update_video_info.assert_called()
        mock_page.open.assert_called()

    @patch("tasks.get_video_info")
    def test_fetch_info_task_failure(self, mock_get_info):
        mock_get_info.return_value = None
        mock_view = MagicMock()
        mock_page = MagicMock()

        # Simulate run_task executing the async callback
        import asyncio
        def run_task_side_effect(func, *args, **kwargs):
            res = func(*args, **kwargs)
            if asyncio.iscoroutine(res):
                asyncio.run(res)
            return res

        mock_page.run_task.side_effect = run_task_side_effect

        fetch_info_task("http://video", mock_view, mock_page)

        # Should raise exception and log error
        mock_page.open.assert_called()  # SnackBar
