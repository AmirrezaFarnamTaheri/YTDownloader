# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for GenericDownloader edge cases.
"""

import threading
import unittest
from unittest.mock import MagicMock, patch

import requests

from downloader.engines.generic import GenericDownloader
from downloader.types import DownloadOptions


class TestGenericDownloaderEdge(unittest.TestCase):
    """Test suite for GenericDownloader edge cases."""

    def setUp(self):
        self.downloader = GenericDownloader()

    @patch("downloader.engines.generic._SESSION.get")
    @patch("downloader.engines.generic._SESSION.head")
    def test_download_retry_logic(self, mock_head, mock_get):
        """Test that download retries on connection errors."""
        # HEAD response
        mock_response_head = MagicMock()
        mock_response_head.headers = {"Content-Length": "1024"}
        mock_response_head.url = "http://example.com/file"
        mock_response_head.status_code = 200
        mock_head.return_value = mock_response_head

        # Success GET response
        mock_response_success = MagicMock()
        mock_response_success.iter_content.return_value = [b"chunk"]
        mock_response_success.status_code = 200
        mock_response_success.headers = {"Content-Length": "1024"}
        mock_response_success.raise_for_status.return_value = None
        # Context manager support
        mock_response_success.__enter__ = MagicMock(return_value=mock_response_success)
        mock_response_success.__exit__ = MagicMock(return_value=None)

        # Fail GET responses (raise exceptions directly)
        mock_get.side_effect = [
            requests.ConnectionError("Fail 1"),
            requests.ConnectionError("Fail 2"),
            mock_response_success,
        ]

        options = DownloadOptions(
            url="http://example.com/file",
            output_path="/tmp/file",
            progress_hook=MagicMock(),
        )

        with patch("builtins.open", unittest.mock.mock_open()):
            with patch("os.path.getsize", return_value=0):
                with patch("time.sleep"):
                    self.downloader.download(
                        url=options.url,
                        output_path=options.output_path,
                        progress_hook=options.progress_hook,
                        cancel_token=options.cancel_token,
                    )

        # Verify it retried (called get 3 times)
        self.assertEqual(mock_get.call_count, 3)

    @patch("downloader.engines.generic._SESSION.get")
    @patch("downloader.engines.generic._SESSION.head")
    def test_download_cancel(self, mock_head, mock_get):
        """Test that download respects cancellation token."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.url = "http://example.com/file"
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        # Infinite stream
        def stream(chunk_size=1024):  # pylint: disable=unused-argument
            while True:
                yield b"chunk"

        mock_response.iter_content.side_effect = stream

        mock_get.return_value = mock_response
        mock_head.return_value = mock_response

        cancel_token = threading.Event()
        options = DownloadOptions(
            url="http://example.com/file",
            output_path="/tmp/file",
            progress_hook=MagicMock(),
            cancel_token=cancel_token,
        )

        # Set cancel token via side effect of progress hook
        def side_effect_hook(d):  # pylint: disable=unused-argument
            cancel_token.set()

        options.progress_hook.side_effect = side_effect_hook

        with patch("builtins.open", unittest.mock.mock_open()):
            with patch("os.path.getsize", return_value=0):
                with self.assertRaises(InterruptedError) as cm:
                    self.downloader.download(
                        url=options.url,
                        output_path=options.output_path,
                        progress_hook=options.progress_hook,
                        cancel_token=options.cancel_token,
                    )

                self.assertIn("Cancelled", str(cm.exception))

    @patch("downloader.engines.generic._SESSION.get")
    @patch("downloader.engines.generic._SESSION.head")
    def test_bad_content_length(self, mock_head, mock_get):
        """Test behavior when Content-Length header is invalid."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "invalid"}
        mock_response.url = "http://example.com/file"
        mock_response.iter_content.return_value = [b"123"]
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        mock_head.return_value = mock_response
        mock_get.return_value = mock_response

        options = DownloadOptions(
            url="http://example.com/file",
            output_path="/tmp/file",
            progress_hook=MagicMock(),
        )

        with patch("builtins.open", unittest.mock.mock_open()):
            self.downloader.download(
                url=options.url,
                output_path=options.output_path,
                progress_hook=options.progress_hook,
            )

        # Verify progress hook called with total_bytes=0 or similar
        args = options.progress_hook.call_args[0][0]
        val = args.get("total_bytes")
        if val is not None:
            self.assertEqual(val, 0)
