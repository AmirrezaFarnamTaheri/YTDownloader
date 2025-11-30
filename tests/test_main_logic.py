import unittest
from unittest.mock import MagicMock, patch, ANY
import threading
import time
from datetime import datetime, timedelta
from tasks_extended import fetch_info_task
from tasks import process_queue, download_task
from app_state import AppState
from utils import CancelToken


class TestMainLogic(unittest.TestCase):

    def setUp(self):
        # Reset singleton state if possible or mock its internals
        self.mock_state = MagicMock()
        self.mock_state.queue_manager = MagicMock()
        self.mock_state.queue_manager.get_all.return_value = []
        self.mock_state.queue_manager.any_downloading.return_value = False
        self.mock_state.queue_manager.claim_next_downloadable.return_value = None
        self.mock_state.current_download_item = None

        # Patch the global state in tasks and main
        self.patcher_main = patch("tasks_extended.state", self.mock_state)
        self.patcher_tasks = patch("tasks.state", self.mock_state)
        self.patcher_main.start()
        self.patcher_tasks.start()

    def tearDown(self):
        self.patcher_main.stop()
        self.patcher_tasks.stop()

    # --- CancelToken Tests ---
    def test_cancel_token(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        self.assertFalse(token.is_paused)

        token.cancel()
        self.assertTrue(token.cancelled)

        with self.assertRaisesRegex(Exception, "Download cancelled by user"):
            token.check({})

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

        token.check({})
        mock_sleep.assert_called_once()

    # --- Process Queue Tests ---

    @patch("tasks.download_task")
    @patch("threading.Thread")
    def test_process_queue_starts_download(self, MockThread, mock_download_task):
        item = {"url": "http://test", "status": "Queued"}
        self.mock_state.queue_manager.claim_next_downloadable.return_value = item

        process_queue()

        MockThread.assert_called_once()
        args, kwargs = MockThread.call_args
        # threading.Thread(target=download_task, args=(item,), daemon=True)
        self.assertEqual(kwargs["target"], mock_download_task)
        self.assertEqual(kwargs["args"][0], item)

    def test_process_queue_scheduled(self):
        future_time = datetime.now() + timedelta(hours=1)
        item = {
            "url": "http://test",
            "status": "Scheduled (future)",
            "scheduled_time": future_time,
        }
        # Mock _queue and _lock for direct access
        self.mock_state.queue_manager._queue = [item]
        self.mock_state.queue_manager._lock = threading.Lock()
        self.mock_state.queue_manager.get_all.return_value = [item]

        process_queue()
        self.assertEqual(item["status"], "Scheduled (future)")  # Should not change

        past_time = datetime.now() - timedelta(hours=1)
        item["scheduled_time"] = past_time
        process_queue()
        self.assertEqual(item["status"], "Queued")
        self.assertIsNone(item["scheduled_time"])

    def test_process_queue_busy(self):
        self.mock_state.queue_manager.any_downloading.return_value = True
        # Concurrency logic changed: we don't bail out on busy anymore, but rely on semaphore.
        # So we expect it to attempt to claim.
        process_queue()
        self.mock_state.queue_manager.claim_next_downloadable.assert_called()

    # --- Download Task Tests ---

    @patch("tasks.download_video")
    @patch("tasks.HistoryManager")
    @patch("tasks.process_queue")
    @patch("threading.Timer")
    def test_download_task_success(
        self, mock_timer, mock_process_queue, MockHistory, mock_download_video
    ):
        # Mock Timer to call function immediately
        mock_timer_instance = MagicMock()
        mock_timer.return_value = mock_timer_instance

        item = {
            "url": "http://test",
            "status": "Queued",
            "control": MagicMock(),
            "output_path": ".",
        }

        download_task(item)

        self.assertEqual(item["status"], "Completed")
        mock_download_video.assert_called_once()
        MockHistory.add_entry.assert_called_once()

        # Timer should be created and started
        mock_timer.assert_called_with(1.0, mock_process_queue)
        mock_timer_instance.start.assert_called_once()

        self.mock_state.current_download_item = None

    @patch("tasks.download_video")
    @patch("tasks.process_queue")
    @patch("threading.Timer")
    def test_download_task_cancelled(self, mock_timer, mock_process_queue, mock_download_video):
        item = {"url": "http://test", "status": "Queued"}
        mock_download_video.side_effect = Exception("Download cancelled by user")

        download_task(item)

        self.assertEqual(item["status"], "Cancelled")

        # Timer should be created
        mock_timer.assert_called_with(1.0, mock_process_queue)

    @patch("tasks.download_video")
    @patch("tasks.process_queue")
    @patch("threading.Timer")
    def test_download_task_error(self, mock_timer, mock_process_queue, mock_download_video):
        item = {"url": "http://test", "status": "Queued"}
        mock_download_video.side_effect = Exception("Network Error")

        download_task(item)

        self.assertEqual(item["status"], "Error")

        # Timer should be created
        mock_timer.assert_called_with(1.0, mock_process_queue)

    @patch("tasks.download_video")
    def test_download_task_progress_hook(self, mock_download_video):
        item = {"url": "http://test", "control": MagicMock()}

        def side_effect(*args, **kwargs):
            hook = args[1]
            # Simulate downloading
            d = {
                "status": "downloading",
                "downloaded_bytes": 50,
                "total_bytes": 100,
                "speed": 1024,
                "eta": 10,
            }
            hook(d, item)
            # Simulate finished
            d_finished = {"status": "finished", "filename": "video.mp4"}
            hook(d_finished, item)

        mock_download_video.side_effect = side_effect

        download_task(item)

        # After download_video returns, it sets status to "Completed"
        self.assertEqual(item["status"], "Completed")

        # Check intermediate calls
        # item['control'].update_progress should have been called multiple times
        self.assertTrue(item["control"].update_progress.call_count >= 2)
        self.assertEqual(item["final_filename"], "video.mp4")

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
        mock_page.open.assert_called()  # With Error
        # mock_download_view.fetch_btn.disabled = False  # Reset button (checked via mock call if needed)
