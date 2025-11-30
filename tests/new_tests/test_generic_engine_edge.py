import unittest
from unittest.mock import MagicMock, patch

import requests

from downloader.engines.generic import download_generic


class TestGenericEngineEdge(unittest.TestCase):
    @patch("downloader.engines.generic.requests.get")
    def test_exhausted_retries_raises_last_error(self, mock_get):
        """Test that last error is raised if all retries fail."""
        # Create a mock exception
        conn_err = requests.exceptions.ConnectionError("Failed connection")

        # Configure raise_for_status to raise the error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = conn_err

        # Configure mock_get to return a context manager that yields the mock response
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_response
        mock_get.return_value = mock_ctx

        with patch("time.sleep"):
            with self.assertRaises(requests.exceptions.ConnectionError):
                download_generic(
                    "http://url", "/tmp", "file.mp4", MagicMock(), {}, max_retries=1
                )


if __name__ == "__main__":
    unittest.main()
