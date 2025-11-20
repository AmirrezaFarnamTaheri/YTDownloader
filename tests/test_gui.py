"""
Comprehensive unit tests for the GUI module.
Tests cover UI initialization, user interactions, and event handling.
"""
import unittest
from unittest.mock import patch, MagicMock, call
import tkinter as tk
from main import YTDownloaderGUI

class TestYTDownloaderGUI(unittest.TestCase):
    """Test cases for YTDownloaderGUI class."""

    def setUp(self):
        """Set up test fixtures."""
        self.root = tk.Tk()
        # Hide window during tests
        self.root.withdraw()
        self.app = YTDownloaderGUI(self.root)

    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass

    def test_gui_initialization(self):
        """Test GUI initializes with correct default state."""
        self.assertEqual(self.app.title_label.cget("text"), "No video loaded")
        self.assertEqual(self.app.duration_label.cget("text"), "Duration: --:--")
        self.assertEqual(self.app.status_label.cget("text"), "Ready")
        self.assertEqual(self.app.progress_bar['value'], 0)
        self.assertEqual(len(self.app.download_queue), 0)

    def test_gui_has_all_tabs(self):
        """Test that all required tabs are present."""
        tabs = [self.app.notebook.tab(i, option='text') for i in range(self.app.notebook.index('end'))]
        # Note: Tabs changed in modern UI
        required_tabs = ['Video', 'Audio', 'Advanced', 'Settings']
        for tab in required_tabs:
            self.assertIn(tab, tabs)

    def test_clear_ui(self):
        """Test clear_ui resets all fields."""
        # Populate some fields
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.title_label.config(text="Test Title")
        self.app.progress_bar['value'] = 50

        # Clear
        self.app.clear_ui()

        # Check reset
        self.assertEqual(self.app.url_entry.get(), "")
        self.assertEqual(self.app.title_label.cget("text"), "No video loaded")
        self.assertEqual(self.app.progress_bar['value'], 0)

    @patch('main.YTDownloaderGUI.show_toast')
    def test_fetch_info_empty_url(self, mock_toast):
        """Test fetch_info with empty URL shows toast."""
        self.app.url_entry.delete(0, tk.END)
        self.app.fetch_info()
        mock_toast.assert_called_once()

    @patch('main.YTDownloaderGUI.show_toast')
    def test_add_to_queue_empty_url(self, mock_toast):
        self.app.url_entry.delete(0, tk.END)
        self.app.add_to_queue()
        mock_toast.assert_called()

    @patch('main.YTDownloaderGUI.show_toast')
    def test_add_to_queue_success(self, mock_toast):
        """Test successful addition to queue."""
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.video_format_var.set("1920x1080 - 22")
        self.app.path_entry.delete(0, tk.END)
        self.app.path_entry.insert(0, ".")

        self.app.add_to_queue()

        self.assertEqual(len(self.app.download_queue), 1)
        self.assertEqual(self.app.download_queue[0]['url'], "https://www.youtube.com/watch?v=test")
        mock_toast.assert_called_with("Added to Queue")

    def test_is_downloading(self):
        """Test is_downloading detection."""
        self.assertFalse(self.app.is_downloading())
        self.app.download_queue.append({'status': 'Queued', 'url': 'test'})
        self.assertFalse(self.app.is_downloading())
        self.app.download_queue[0]['status'] = 'Downloading'
        self.assertTrue(self.app.is_downloading())

    @patch('main.YTDownloaderGUI.show_toast')
    def test_remove_from_queue(self, mock_toast):
        # Add items
        self.app.download_queue.append({'url': '1', 'status': 'Queued'})
        self.app.download_queue.append({'url': '2', 'status': 'Queued'})
        self.app.update_download_queue_list()

        # Select and remove
        self.app.download_queue_tree.selection_set(self.app.download_queue_tree.get_children()[0])
        self.app.remove_from_queue()

        self.assertEqual(len(self.app.download_queue), 1)
        self.assertEqual(self.app.download_queue[0]['url'], '2')

    def test_process_ui_queue(self):
        mock_func = MagicMock()
        self.app.ui_queue.put((mock_func, {'a': 1}))
        self.app.process_ui_queue()
        mock_func.assert_called_with(a=1)

    @patch('main.messagebox.showerror')
    def test_handle_error_threadsafe(self, mock_showerror):
        # queue the error
        self.app.handle_error_threadsafe("Title", "Error")
        # process queue
        self.app.process_ui_queue()
        mock_showerror.assert_called_with("Title", "Error")

if __name__ == '__main__':
    unittest.main()
