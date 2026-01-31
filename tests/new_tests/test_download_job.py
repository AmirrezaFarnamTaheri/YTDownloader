"""
Tests for DownloadJob class in tasks.py
"""

import unittest
from unittest.mock import MagicMock, patch

from downloader.types import DownloadStatus
from tasks import DownloadJob

class TestDownloadJob(unittest.TestCase):
    def setUp(self):
        self.mock_page = MagicMock()
        self.item = {"id": "123", "url": "http://test.com", "title": "Test Video"}

    @patch("tasks.app_state.state")
    @patch("tasks.download_video")
    def test_run_success(self, mock_download, mock_state):
        # Setup mocks
        qm = MagicMock()
        mock_state.queue_manager = qm
        mock_state.config.get.return_value = "."

        # Ensure shutdown flag is not set
        mock_state.shutdown_flag.is_set.return_value = False

        # Setup download result
        mock_download.return_value = {"filename": "video.mp4"}

        job = DownloadJob(self.item, self.mock_page)
        job.run()

        # Verify interactions
        # 1. Register token
        qm.register_cancel_token.assert_called_with("123", job.cancel_token)

        # 2. Update status to Downloading
        qm.update_item_status.assert_any_call("123", DownloadStatus.DOWNLOADING)

        # 3. Call download
        mock_download.assert_called_once()

        # 4. Update status to Completed
        # Note: assert_called_with checks only the LAST call.
        # We want to ensure it was called with COMPLETED.
        # But handle_error might be called if mock_download fails.
        # Here it succeeds.

        # Check call args list
        calls = qm.update_item_status.call_args_list
        self.assertTrue(any(c[0][1] == DownloadStatus.COMPLETED for c in calls))

        # 5. Unregister token
        qm.unregister_cancel_token.assert_called_with("123", job.cancel_token)

    @patch("tasks.app_state.state")
    @patch("tasks.download_video")
    def test_run_failure(self, mock_download, mock_state):
        qm = MagicMock()
        mock_state.queue_manager = qm
        mock_state.shutdown_flag.is_set.return_value = False
        mock_download.side_effect = Exception("Network Fail")

        job = DownloadJob(self.item, self.mock_page)
        job.run()

        calls = qm.update_item_status.call_args_list
        self.assertTrue(any(c[0][1] == DownloadStatus.ERROR for c in calls))

if __name__ == "__main__":
    unittest.main()
