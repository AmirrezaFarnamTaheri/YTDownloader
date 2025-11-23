import pytest
from unittest.mock import MagicMock, patch, mock_open
import requests
import os
from downloader.engines.generic import download_generic

class TestGenericEngineExtra:

    @patch("downloader.engines.generic.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_retry_logic(self, mock_getsize, mock_exists, mock_file, mock_get):
        # Setup: file doesn't exist initially
        mock_exists.return_value = False

        # Requests raises exception 3 times then succeeds?
        # Or fails all times.
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        hook = MagicMock()
        item = {}

        with patch("time.sleep"): # Speed up test
            with pytest.raises(requests.exceptions.RequestException):
                download_generic(
                    "http://u.com", "/tmp", "f.mp4", hook, item, max_retries=2
                )

        assert mock_get.call_count == 3

    @patch("downloader.engines.generic.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_resume_logic_206(self, mock_getsize, mock_exists, mock_file, mock_get):
        mock_exists.return_value = True
        mock_getsize.return_value = 100

        mock_response = MagicMock()
        mock_response.status_code = 206
        mock_response.headers = {"Content-Range": "bytes 100-200/200", "content-length": "100"}
        mock_response.iter_content.return_value = [b"data"]
        mock_get.return_value.__enter__.return_value = mock_response

        hook = MagicMock()
        item = {}

        download_generic("http://u.com", "/tmp", "f.mp4", hook, item)

        # Verify mode is 'ab'
        mock_file.assert_called_with(os.path.join("/tmp", "f.mp4"), "ab")
        # Verify headers had Range
        args, kwargs = mock_get.call_args
        assert kwargs["headers"]["Range"] == "bytes=100-"

    @patch("downloader.engines.generic.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_resume_logic_200_reset(self, mock_getsize, mock_exists, mock_file, mock_get):
        # File exists (100 bytes) but server returns 200 (full content)
        mock_exists.return_value = True
        mock_getsize.return_value = 100

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "200"}
        mock_response.iter_content.return_value = [b"data"]
        mock_get.return_value.__enter__.return_value = mock_response

        hook = MagicMock()
        item = {}

        download_generic("http://u.com", "/tmp", "f.mp4", hook, item)

        # Verify mode is 'wb' (overwrite)
        mock_file.assert_called_with(os.path.join("/tmp", "f.mp4"), "wb")

    def test_cancel_exception(self):
        hook = MagicMock()
        item = {}
        token = MagicMock()
        token.check.side_effect = Exception("Cancelled")

        with patch("downloader.engines.generic.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.iter_content.return_value = [b"chunk"]
            mock_get.return_value.__enter__.return_value = mock_response

            with patch("builtins.open", mock_open()):
                with pytest.raises(Exception, match="Cancelled"):
                    download_generic("http://u.com", "/tmp", "f.mp4", hook, item, cancel_token=token)
