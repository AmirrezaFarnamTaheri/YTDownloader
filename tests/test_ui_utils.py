# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Unit tests for UI utility functions.
"""

import unittest
from unittest.mock import patch

from ui_utils import (
    format_file_size,
    is_ffmpeg_available,
    validate_download_path,
    validate_proxy,
    validate_rate_limit,
    validate_url,
)


class TestUIUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def test_validate_url(self):
        self.assertTrue(validate_url("https://www.youtube.com/watch?v=test"))
        self.assertFalse(validate_url("ftp://test.com"))
        self.assertFalse(validate_url("short"))

    def test_validate_proxy(self):
        self.assertTrue(validate_proxy(""))
        self.assertFalse(validate_proxy("http://127.0.0.1:8080"))
        self.assertFalse(validate_proxy("invalid"))

    def test_validate_rate_limit(self):
        self.assertTrue(validate_rate_limit(""))
        self.assertTrue(validate_rate_limit("50K"))
        self.assertTrue(validate_rate_limit("10M"))
        self.assertFalse(validate_rate_limit("invalid"))

    def test_validate_download_path(self):
        self.assertTrue(validate_download_path(""))
        self.assertTrue(validate_download_path(None))
        self.assertFalse(validate_download_path(123))

    def test_format_file_size(self):
        self.assertEqual(format_file_size(None), "N/A")
        self.assertEqual(format_file_size(0), "0.00 B")
        self.assertEqual(format_file_size(1024), "1.00 KB")
        self.assertEqual(format_file_size(1048576), "1.00 MB")

    @patch("shutil.which")
    def test_is_ffmpeg_available_true(self, mock_which):
        import ui_utils

        # Reset cache
        ui_utils._ffmpeg_available_cache = None

        mock_which.return_value = "/usr/bin/ffmpeg"
        self.assertTrue(is_ffmpeg_available())

    @patch("shutil.which")
    def test_is_ffmpeg_available_false(self, mock_which):
        import ui_utils

        # Reset cache
        ui_utils._ffmpeg_available_cache = None

        mock_which.return_value = None
        self.assertFalse(is_ffmpeg_available())


if __name__ == "__main__":
    unittest.main()
