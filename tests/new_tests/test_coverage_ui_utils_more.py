
import unittest
from unittest.mock import MagicMock, patch
import ui_utils

class TestUIUtilsMore(unittest.TestCase):
    def test_open_folder(self):
        page = MagicMock()
        page.platform = "linux"
        with patch("subprocess.Popen") as mock_popen, \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.exists", return_value=True):
            ui_utils.open_folder("/tmp", page)
            mock_popen.assert_called()

    def test_open_folder_windows(self):
        page = MagicMock()
        page.platform = "windows"
        with patch("os.startfile") as mock_start, \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.exists", return_value=True), \
             patch("sys.platform", "win32"):
            ui_utils.open_folder("C:\\", page)
            mock_start.assert_called()

    def test_play_file(self):
        page = MagicMock()
        page.platform = "linux"
        with patch("subprocess.Popen") as mock_popen, \
             patch("os.path.exists", return_value=True):
            ui_utils.play_file("/tmp/vid.mp4", page)
            mock_popen.assert_called()

    def test_validate_proxy_valid(self):
        self.assertTrue(ui_utils.validate_proxy("http://127.0.0.1:8080"))
        self.assertTrue(ui_utils.validate_proxy("socks5://user:pass@host:1080"))

    def test_validate_proxy_invalid(self):
        self.assertFalse(ui_utils.validate_proxy("ftp://host"))
        self.assertFalse(ui_utils.validate_proxy("notaproxy"))

    def test_format_size(self):
        self.assertEqual(ui_utils.format_size(1024), "1.00 KB")
        self.assertEqual(ui_utils.format_size(1048576), "1.00 MB")
        self.assertEqual(ui_utils.format_size(0), "0 B")
