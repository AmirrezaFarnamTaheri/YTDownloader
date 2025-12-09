"""
Tests for recent audit fixes and security enhancements.
"""

import os
import unittest
from datetime import datetime, time
from pathlib import Path
from unittest.mock import MagicMock, patch

from batch_importer import BatchImporter
from download_scheduler import DownloadScheduler
from downloader.types import DownloadOptions
from ui_utils import is_safe_path, validate_output_template, validate_proxy


class TestAuditFixes(unittest.TestCase):
    """Tests for security and validation improvements."""

    def test_validate_proxy_strict(self):
        """Test strict proxy validation."""
        # Valid Public IP
        self.assertTrue(validate_proxy("http://8.8.8.8:8080"))

        # Private IPs should be BLOCKED
        self.assertFalse(validate_proxy("http://10.0.0.1:8080"))
        self.assertFalse(validate_proxy("http://192.168.1.1:8080"))
        self.assertFalse(validate_proxy("http://127.0.0.1:8080"))
        self.assertFalse(validate_proxy("http://localhost:8080"))

        # Public IP
        self.assertTrue(validate_proxy("http://8.8.8.8:8080"))
        self.assertTrue(validate_proxy("socks5://user:pass@proxy.example.com:1080"))

        # Invalid Scheme
        self.assertFalse(validate_proxy("ftp://proxy.com:80"))

    def test_validate_output_template(self):
        """Test output template validation."""
        self.assertTrue(validate_output_template("%(title)s.%(ext)s"))
        self.assertTrue(validate_output_template("folder/%(title)s.mp4"))

        # Invalid
        self.assertFalse(validate_output_template("/absolute/path/%(title)s"))
        self.assertFalse(validate_output_template("../parent/%(title)s"))
        self.assertFalse(validate_output_template("folder/../../hack"))

    def test_is_safe_path(self):
        """Test safe path checking."""
        home = Path.home()
        safe_path = home / "Downloads" / "file.txt"
        unsafe_path = Path("/etc/passwd") if os.name != "nt" else Path("C:\\Windows\\System32")

        self.assertTrue(is_safe_path(str(safe_path)))
        if os.name != "nt":
            self.assertFalse(is_safe_path("/etc/passwd"))
            self.assertFalse(is_safe_path("/var/log"))

    def test_download_options_filename(self):
        """Test filename sanitization in DownloadOptions."""
        opts = DownloadOptions(url="http://example.com")
        opts.validate() # Should pass

        opts.filename = "clean_name.mp4"
        opts.validate() # Should pass

        opts.filename = "hacked/name.mp4"
        with self.assertRaises(ValueError):
            opts.validate()

        opts.filename = "..\\windows.mp4"
        with self.assertRaises(ValueError):
            opts.validate()

        opts.filename = ".."
        with self.assertRaises(ValueError):
            opts.validate()

    @patch("batch_importer.is_safe_path")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_batch_importer_security(self, mock_is_file, mock_exists, mock_is_safe):
        """Test batch importer security check."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        importer = BatchImporter(MagicMock(), MagicMock())

        # Unsafe
        mock_is_safe.return_value = False
        with self.assertRaises(ValueError) as cm:
            importer.import_from_file("/etc/passwd.txt")
        self.assertIn("Security", str(cm.exception))

        # Safe
        # (We don't need to test successful import logic here, just the guard)

    def test_scheduler_datetime(self):
        """Test scheduler accepts datetime."""
        # Time
        status, dt = DownloadScheduler.prepare_schedule(time(12, 0))
        self.assertIn("Scheduled", status)
        self.assertIsInstance(dt, datetime)

        # Datetime
        target = datetime(2025, 1, 1, 12, 0)
        status, dt = DownloadScheduler.prepare_schedule(target)
        self.assertIn("2025-01-01", status)
        self.assertEqual(dt, target)

if __name__ == "__main__":
    unittest.main()
