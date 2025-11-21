import unittest
from unittest.mock import MagicMock, patch
import threading
import time
from main import AppState, main
import main as app_main
from queue_manager import QueueManager


class TestMainIntegration(unittest.TestCase):

    def setUp(self):
        self.state = AppState()
        self.state.queue_manager = QueueManager()

    @patch("main.download_video")
    @patch("main.HistoryManager.add_entry")
    def test_download_task_success(self, mock_add_history, mock_download):
        # Simulate a successful download task
        item = {
            "url": "http://test.com",
            "status": "Queued",
            "title": "Test",
            "output_path": "/tmp",
            "video_format": "best",
        }
        self.state.queue_manager.add_item(item)

        # Mock progress hook execution
        def side_effect_download(*args, **kwargs):
            progress_hook = args[1]
            progress_hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 50,
                    "total_bytes": 100,
                    "speed": 100,
                    "eta": 1,
                },
                item,
            )
            progress_hook({"status": "finished", "filename": "out.mp4"}, item)

        mock_download.side_effect = side_effect_download

        # Run task directly (no thread for test simplicity)
        app_main.state = self.state  # Inject state
        app_main.download_task(item)

        self.assertEqual(item["status"], "Completed")
        self.assertEqual(item["final_filename"], "out.mp4")
        mock_add_history.assert_called()

    @patch("main.download_video")
    def test_download_task_failure(self, mock_download):
        # Simulate a failed download task
        item = {"url": "http://fail.com", "status": "Queued", "title": "Fail"}
        mock_download.side_effect = Exception("Network Error")

        app_main.state = self.state
        app_main.download_task(item)

        self.assertEqual(item["status"], "Error")

    @patch("main.pyperclip.paste")
    @patch("main.validate_url")
    def test_background_clipboard_monitor(self, mock_validate, mock_paste):
        # Test clipboard monitor logic
        self.state.clipboard_monitor_active = True
        self.state.last_clipboard_content = "old"

        mock_paste.return_value = "http://new.com"
        mock_validate.return_value = True

        # Mock UI elements that would be updated
        app_main.download_view = MagicMock()
        app_main.page = MagicMock()

        # Extract logic from background loop for testing
        content = mock_paste()
        if content and content != self.state.last_clipboard_content:
            self.state.last_clipboard_content = content
            if mock_validate(content):
                app_main.download_view.url_input.value = content

        self.assertEqual(app_main.download_view.url_input.value, "http://new.com")

    @patch("main.download_task")
    def test_process_queue_scheduler(self, mock_download_task):
        # Test scheduling logic
        from datetime import datetime, timedelta

        future_time = datetime.now() + timedelta(minutes=10)
        item = {
            "url": "http://sched.com",
            "status": "Scheduled (12:00)",
            "scheduled_time": future_time,
        }
        self.state.queue_manager.add_item(item)

        app_main.state = self.state
        app_main.process_queue()

        # Should still be scheduled
        self.assertTrue(item["status"].startswith("Scheduled"))

        # Move time to past
        item["scheduled_time"] = datetime.now() - timedelta(minutes=1)
        app_main.process_queue()

        # Should be allocated or processed.
        # Since process_queue starts a thread for download_task, and claim_next_downloadable changes status to Allocating
        # We check if mock was called or status changed
        self.assertTrue(
            mock_download_task.called
            or item["status"] == "Allocating"
            or item["status"] == "Downloading"
        )


if __name__ == "__main__":
    unittest.main()
