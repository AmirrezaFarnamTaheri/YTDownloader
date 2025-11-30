import os
import unittest
from unittest.mock import MagicMock, patch

import requests

from downloader.engines.generic import download_generic


class TestGenericEngineExtra(unittest.TestCase):
    @patch("downloader.engines.generic.requests.get")
    def test_progress_update_logic(self, mock_get):
        """Test that progress updates trigger correctly."""
        # Setup mock response with enough chunks to trigger update
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        # Create enough small chunks to ensure time passes or iteration happens
        # Note: We rely on time passing, so we might need to mock time
        mock_response.iter_content.return_value = [b"a" * 100] * 10
        mock_get.return_value.__enter__.return_value = mock_response

        progress_hook = MagicMock()

        # Mock time to ensure we hit the 0.1s update threshold
        # Use a mutable list to track time and increment on each call to avoid StopIteration
        # caused by extra logging calls that access time.time()
        current_time = [0.0]

        def increment_time():
            t = current_time[0]
            current_time[0] += 0.2
            return t

        with patch("time.time", side_effect=increment_time):
            with patch("builtins.open", new_callable=MagicMock):
                download_generic("http://url", "/tmp", "file.mp4", progress_hook, {})

        # Verify progress hook was called with "downloading" status
        calls = [
            c
            for c in progress_hook.call_args_list
            if c[0][0]["status"] == "downloading"
        ]
        self.assertTrue(len(calls) > 0)

    @patch("downloader.engines.generic.requests.get")
    def test_retry_resume_logic(self, mock_get):
        """Test that retries set the Range header correctly."""
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

        # Check that second call had Range header
        args, kwargs = mock_get.call_args_list[1]
        self.assertIn("Range", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["Range"], "bytes=500-")

    @patch("downloader.engines.generic.requests.get")
    def test_exhausted_retries_raises_last_error(self, mock_get):
        """Test that last error is raised if all retries fail."""
        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = requests.exceptions.ConnectionError(
            "Fail"
        )

        ctx = MagicMock()
        ctx.__enter__.return_value = mock_fail
        mock_get.return_value = ctx

        with patch("time.sleep"):
            with self.assertRaises(requests.exceptions.ConnectionError):
                download_generic(
                    "http://url", "/tmp", "file.mp4", MagicMock(), {}, max_retries=1
                )

    @patch("downloader.engines.generic.requests.get")
    def test_retry_without_file_exists(self, mock_get):
        """Test retry logic when partial file does not exist."""
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

        # Check that second call did NOT have Range header (or at least not for bytes=500-)
        args, kwargs = mock_get.call_args_list[1]
        self.assertNotIn("Range", kwargs["headers"])


if __name__ == "__main__":
    unittest.main()
