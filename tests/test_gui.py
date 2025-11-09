import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
from main import YTDownloaderGUI

class TestGUI(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = YTDownloaderGUI(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_initial_ui_state(self):
        self.assertEqual(self.app.title_label.cget("text"), "Title: N/A")
        self.assertEqual(self.app.duration_label.cget("text"), "Duration: N/A")
        self.assertEqual(self.app.status_label.cget("text"), "")
        self.assertEqual(self.app.progress_bar['value'], 0)

    def test_fetch_info_button(self):
        with patch.object(self.app, 'fetch_info') as mock_fetch_info:
            self.app.fetch_info()
            mock_fetch_info.assert_called_once()

    def test_add_to_queue_button(self):
        with patch.object(self.app, 'add_to_queue') as mock_add_to_queue:
            self.app.add_to_queue()
            mock_add_to_queue.assert_called_once()

    def test_cancel_button(self):
        with patch.object(self.app, 'cancel_download') as mock_cancel_download:
            self.app.cancel_download()
            mock_cancel_download.assert_called_once()

    def test_clear_ui(self):
        self.app.url_entry.insert(0, "test_url")
        self.app.title_label.config(text="Test Title")
        self.app.clear_ui()
        self.assertEqual(self.app.url_entry.get(), "")
        self.assertEqual(self.app.title_label.cget("text"), "Title: N/A")

if __name__ == '__main__':
    unittest.main()
