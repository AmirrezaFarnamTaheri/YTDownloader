import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

import requests

from downloader.engines.generic import download_generic


class TestGenericDownloaderCoverage(unittest.TestCase):

    @patch("requests.head")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.getsize")
    @patch("os.path.exists")
    @patch("downloader.engines.generic.validate_url")
    @patch("os.path.isdir")
    def test_download_generic_success(
        self,
        mock_isdir,
        mock_validate_url,
        mock_exists,
        mock_getsize,
        mock_file,
        mock_get,
        mock_head,
    ):
        mock_validate_url.return_value = True
        mock_isdir.return_value = True

        # Setup clean download
        mock_exists.return_value = False

        # HEAD response
        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.headers = {"content-length": "1000"}
        mock_head_resp.url = "http://url"
        mock_head.return_value = mock_head_resp

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]

        mock_get.return_value.__enter__.return_value = mock_response

        progress_hook = MagicMock()

        download_generic("http://url", "/tmp", "file.mp4", progress_hook, {})

        # Verify file opened in wb mode
        # Path join is platform specific, but we usually expect /tmp/file.mp4
        mock_file.assert_called_with(os.path.join("/tmp", "file.mp4"), "wb")

        # Verify writes
        handle = mock_file()
        handle.write.assert_any_call(b"chunk1")

        # Verify progress calls
        self.assertTrue(progress_hook.called)

    @patch("requests.head")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.getsize")
    @patch("os.path.exists")
    @patch("downloader.engines.generic.validate_url")
    @patch("os.path.isdir")
    def test_download_generic_resume_success(
        self,
        mock_isdir,
        mock_validate_url,
        mock_exists,
        mock_getsize,
        mock_file,
        mock_get,
        mock_head,
    ):
        mock_validate_url.return_value = True
        mock_isdir.return_value = True

        mock_exists.return_value = True
        mock_getsize.return_value = 500

        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.headers = {"content-length": "1000"}
        mock_head_resp.url = "http://url"
        mock_head.return_value = mock_head_resp

        mock_response = MagicMock()
        mock_response.status_code = 206  # Partial
        mock_response.headers = {
            "content-length": "500",
            "Content-Range": "bytes 500-1000/1000",
        }
        mock_response.iter_content.return_value = [b"chunk3"]

        mock_get.return_value.__enter__.return_value = mock_response

        download_generic("http://url", "/tmp", "file.mp4", MagicMock(), {})

        # Verify file opened in ab mode
        mock_file.assert_called_with(os.path.join("/tmp", "file.mp4"), "ab")

        # Verify request headers contained Range
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"]["Range"], "bytes=500-")

    @patch("requests.head")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.getsize")
    @patch("os.path.exists")
    @patch("downloader.engines.generic.validate_url")
    @patch("os.path.isdir")
    def test_download_generic_resume_fail_restart(
        self,
        mock_isdir,
        mock_validate_url,
        mock_exists,
        mock_getsize,
        mock_file,
        mock_get,
        mock_head,
    ):
        mock_validate_url.return_value = True
        mock_isdir.return_value = True

        mock_exists.return_value = True
        mock_getsize.return_value = 500

        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.headers = {"content-length": "1000"}
        mock_head_resp.url = "http://url"
        mock_head.return_value = mock_head_resp

        mock_response = MagicMock()
        mock_response.status_code = 200  # Full content, resume refused
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"chunk1"]

        mock_get.return_value.__enter__.return_value = mock_response

        download_generic("http://url", "/tmp", "file.mp4", MagicMock(), {})

        # Should switch to wb mode
        mock_file.assert_called_with(os.path.join("/tmp", "file.mp4"), "wb")

    @patch("requests.head")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("time.sleep")
    @patch("downloader.engines.generic.validate_url")
    @patch("os.path.isdir")
    @patch("os.path.exists")
    def test_download_generic_retry(
        self,
        mock_exists,
        mock_isdir,
        mock_validate_url,
        mock_sleep,
        mock_file,
        mock_get,
        mock_head,
    ):
        mock_validate_url.return_value = True
        mock_isdir.return_value = True
        mock_exists.return_value = False

        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.headers = {"content-length": "10"}
        mock_head_resp.url = "http://url"
        mock_head.return_value = mock_head_resp

        # Fail twice, succeed third time
        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = requests.exceptions.ConnectionError(
            "fail"
        )

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.headers = {"content-length": "10"}
        mock_success.iter_content.return_value = [b"data"]

        mock_get.return_value.__enter__.side_effect = [
            requests.exceptions.ConnectionError("conn err"),  # Raise during enter
            requests.exceptions.ConnectionError("conn err"),
            mock_success,
        ]

        download_generic("http://url", "/tmp", "file.mp4", MagicMock(), {})

        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("requests.head")
    @patch("requests.get")
    @patch("time.sleep")
    @patch("downloader.engines.generic.validate_url")
    @patch("os.path.isdir")
    @patch("os.path.exists")
    def test_download_generic_max_retries_exceeded(
        self,
        mock_exists,
        mock_isdir,
        mock_validate_url,
        mock_sleep,
        mock_get,
        mock_head,
    ):
        mock_validate_url.return_value = True
        mock_isdir.return_value = True
        mock_exists.return_value = False

        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.headers = {"content-length": "10"}
        mock_head_resp.url = "http://url"
        mock_head.return_value = mock_head_resp

        mock_get.side_effect = requests.exceptions.ConnectionError("fail")

        with self.assertRaises(requests.exceptions.ConnectionError):
            download_generic(
                "http://url", "/tmp", "file.mp4", MagicMock(), {}, max_retries=2
            )

        self.assertEqual(mock_get.call_count, 3)  # initial + 2 retries

    @patch("requests.head")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("downloader.engines.generic.validate_url")
    @patch("os.path.isdir")
    @patch("os.path.exists")
    def test_download_generic_cancellation(
        self, mock_exists, mock_isdir, mock_validate_url, mock_file, mock_get, mock_head
    ):
        mock_validate_url.return_value = True
        mock_isdir.return_value = True
        mock_exists.return_value = False

        mock_head_resp = MagicMock()
        mock_head_resp.status_code = 200
        mock_head_resp.headers = {"content-length": "10"}
        mock_head_resp.url = "http://url"
        mock_head.return_value = mock_head_resp

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"chunk"]
        mock_get.return_value.__enter__.return_value = mock_response

        token = MagicMock()
        token.check.side_effect = Exception("Cancelled")

        with self.assertRaises(InterruptedError) as cm:
            download_generic(
                "http://url",
                "/tmp",
                "file.mp4",
                MagicMock(),
                cancel_token=token,
                max_retries=3,
            )

        self.assertEqual(str(cm.exception), "Download Cancelled by user")
