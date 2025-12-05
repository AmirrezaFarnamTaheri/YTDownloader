"""
Extra coverage tests for GenericDownloader engine.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from downloader.engines.generic import download_generic


class TestGenericEngineExtra(unittest.TestCase):
    """Test suite for GenericDownloader extra coverage."""

    @patch(
        "downloader.engines.generic.validate_url", return_value=True
    )  # Mock validation
    @patch("downloader.engines.generic.requests.get")
    def test_progress_update_logic(self, mock_get, mock_validate):
        """Test that progress updates trigger correctly."""
        # Unused arguments
        del mock_validate

        # Setup mock response with enough chunks to trigger update
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"a" * 100] * 10
        mock_get.return_value.__enter__.return_value = mock_response

        progress_hook = MagicMock()

        # Mock time to ensure we hit the 0.1s update threshold
        # Use a mutable list to track time and increment on each call
        current_time = [0.0]

        def increment_time():
            t = current_time[0]
            current_time[0] += 0.2
            return t

        with patch("time.time", side_effect=increment_time):
            with patch("builtins.open", new_callable=MagicMock):
                download_generic("http://url", "/tmp", "file.mp4", progress_hook, {})

        # Should have called hook multiple times
        self.assertTrue(progress_hook.call_count > 1)

    @patch("downloader.engines.generic.validate_url", return_value=True)
    @patch("downloader.engines.generic.requests.get")
    def test_retry_resume_logic(self, mock_get, mock_validate):
        """Test that retries set the Range header correctly."""
        # Unused arguments
        del mock_validate

        # First attempt fails with connection error
        # Second attempt succeeds
        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = requests.exceptions.ConnectionError(
            "Fail"
        )

        mock_success = MagicMock()
        mock_success.status_code = 206
        mock_success.iter_content.return_value = []

        # Mock context manager structure
        fail_ctx = MagicMock()
        fail_ctx.__enter__.return_value = mock_fail

        success_ctx = MagicMock()
        success_ctx.__enter__.return_value = mock_success

        mock_get.side_effect = [fail_ctx, success_ctx]

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=500):
                with patch("time.sleep"):  # Skip sleep
                    download_generic("http://url", "/tmp", "file.mp4", MagicMock(), {})

        # Verify Range header on second call
        self.assertEqual(mock_get.call_count, 2)
        _, kwargs = mock_get.call_args_list[1]
        self.assertEqual(kwargs["headers"]["Range"], "bytes=500-")

    @patch("downloader.engines.generic.validate_url", return_value=True)
    @patch("downloader.engines.generic.requests.get")
    def test_exhausted_retries_raises_last_error(self, mock_get, mock_validate):
        """Test that exception is re-raised after max retries."""
        # Unused arguments
        del mock_validate

        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = requests.exceptions.ConnectionError(
            "Final Fail"
        )
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_fail
        mock_get.return_value = ctx

        with patch("time.sleep"):
            with self.assertRaises(requests.exceptions.ConnectionError):
                download_generic(
                    "http://url", "/tmp", "file.mp4", MagicMock(), {}, max_retries=2
                )

        # Initial + 2 retries = 3 calls
        self.assertEqual(mock_get.call_count, 3)

    @patch("downloader.engines.generic.validate_url", return_value=True)
    @patch("downloader.engines.generic.requests.get")
    def test_retry_without_file_exists(self, mock_get, mock_validate):
        """Test retry logic when partial file does not exist."""
        # Unused arguments
        del mock_validate

        # First attempt fails
        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = requests.exceptions.ConnectionError(
            "Fail"
        )

        # Second attempt succeeds
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.iter_content.return_value = []

        fail_ctx = MagicMock()
        fail_ctx.__enter__.return_value = mock_fail

        success_ctx = MagicMock()
        success_ctx.__enter__.return_value = mock_success

        mock_get.side_effect = [fail_ctx, success_ctx]

        # Force os.path.exists to return False
        with patch("os.path.exists", return_value=False):
            with patch("time.sleep"):
                download_generic("http://url", "/tmp", "file.mp4", MagicMock(), {})

        # Verify Range header NOT set on second call
        _, kwargs = mock_get.call_args_list[1]
        self.assertNotIn("Range", kwargs["headers"])
