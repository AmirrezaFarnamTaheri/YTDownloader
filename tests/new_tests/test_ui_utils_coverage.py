"""
Tests for ui_utils module coverage.
"""

import unittest
from unittest.mock import ANY, patch

import ui_utils


class TestUIUtilsCoverage(unittest.TestCase):
    """Test suite for ui_utils coverage."""

    def test_format_file_size_extended(self):
        """Test extended file size formatting cases."""
        # Additional cases
        self.assertEqual(ui_utils.format_file_size(None), "N/A")
        self.assertEqual(ui_utils.format_file_size("invalid"), "N/A")
        self.assertEqual(ui_utils.format_file_size(0), "0.00 B")
        self.assertEqual(ui_utils.format_file_size(1023), "1023.00 B")
        self.assertEqual(ui_utils.format_file_size(1024), "1.00 KB")
        # Very large
        self.assertEqual(ui_utils.format_file_size(1024**5), "1.00 PB")
        self.assertEqual(
            ui_utils.format_file_size(1024**6), "1024.00 PB"
        )  # Loop finishes at PB

    def test_validate_url_extended(self):
        """Test extended URL validation cases."""
        self.assertFalse(ui_utils.validate_url(None))  # type: ignore
        self.assertFalse(ui_utils.validate_url(123))  # type: ignore
        self.assertFalse(ui_utils.validate_url("   "))
        self.assertFalse(ui_utils.validate_url("ftp://example.com"))  # Only http/s
        self.assertFalse(ui_utils.validate_url("http://"))  # Too short

        # Regex check
        self.assertTrue(ui_utils.validate_url("http://example.com"))
        self.assertFalse(
            ui_utils.validate_url("http://ex ample.com")
        )  # Space not allowed

    def test_validate_proxy_extended(self):
        """Test extended proxy validation cases."""
        self.assertTrue(ui_utils.validate_proxy(None))  # type: ignore
        self.assertTrue(ui_utils.validate_proxy(""))

        self.assertFalse(ui_utils.validate_proxy("http://no-port"))
        self.assertFalse(ui_utils.validate_proxy("invalid://host:80"))

        # Auth case
        self.assertTrue(ui_utils.validate_proxy("http://user:pass@host:8080"))
        self.assertFalse(ui_utils.validate_proxy("http://user:pass@host"))  # No port

        # Port range
        self.assertFalse(ui_utils.validate_proxy("http://host:0"))
        self.assertFalse(ui_utils.validate_proxy("http://host:70000"))

        # Empty host
        self.assertFalse(ui_utils.validate_proxy("http://:8080"))

    def test_validate_rate_limit_extended(self):
        """Test extended rate limit validation cases."""
        self.assertTrue(ui_utils.validate_rate_limit(None))  # type: ignore
        self.assertTrue(ui_utils.validate_rate_limit(""))

        self.assertTrue(ui_utils.validate_rate_limit("50K"))
        self.assertTrue(ui_utils.validate_rate_limit("1.5M"))

        self.assertFalse(ui_utils.validate_rate_limit("0K"))  # Zero value
        self.assertFalse(ui_utils.validate_rate_limit("invalid"))
        self.assertFalse(ui_utils.validate_rate_limit("100KK"))

    @patch("shutil.which")
    def test_is_ffmpeg_available(self, mock_which):
        """Test ffmpeg availability check."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        self.assertTrue(ui_utils.is_ffmpeg_available())

        mock_which.return_value = None
        self.assertFalse(ui_utils.is_ffmpeg_available())

    @patch("os.path.isdir")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("subprocess.Popen")
    @patch("os.startfile", create=True)
    def test_open_folder(
        self, mock_startfile, mock_popen, mock_expand, mock_exists, mock_isdir
    ):
        """Test open_folder logic for different platforms."""
        # Path empty
        self.assertFalse(ui_utils.open_folder(None))  # type: ignore

        mock_expand.return_value = "/path/to/folder"

        # Path not exists
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertFalse(ui_utils.open_folder("/path/to/folder"))

        mock_exists.return_value = True
        mock_isdir.return_value = True

        # Windows
        with patch("platform.system", return_value="Windows"):
            self.assertTrue(ui_utils.open_folder("/path/to/folder"))
            mock_startfile.assert_called_with("/path/to/folder")

        # Darwin
        with patch("platform.system", return_value="Darwin"):
            self.assertTrue(ui_utils.open_folder("/path/to/folder"))
            mock_popen.assert_called_with(
                ["open", "/path/to/folder"], stdout=ANY, stderr=ANY
            )

        # Linux
        with patch("platform.system", return_value="Linux"):
            self.assertTrue(ui_utils.open_folder("/path/to/folder"))
            mock_popen.assert_called_with(
                ["xdg-open", "/path/to/folder"], stdout=ANY, stderr=ANY
            )

        # Exception handling
        with patch("platform.system", return_value="Linux"):
            mock_popen.side_effect = Exception("Failed")
            self.assertFalse(ui_utils.open_folder("/path/to/folder"))
