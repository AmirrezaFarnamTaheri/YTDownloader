"""
Comprehensive unit tests for the GUI module.
Tests cover UI initialization, user interactions, and event handling.
"""
import unittest
from unittest.mock import patch, MagicMock, call
import tkinter as tk
from pathlib import Path
from main import YTDownloaderGUI, validate_url, validate_proxy, validate_rate_limit, format_file_size


class TestValidationFunctions(unittest.TestCase):
    """Test cases for validation helper functions."""

    def test_validate_url_valid_http(self):
        """Test validation of valid HTTP URL."""
        self.assertTrue(validate_url("http://www.youtube.com/watch?v=test"))

    def test_validate_url_valid_https(self):
        """Test validation of valid HTTPS URL."""
        self.assertTrue(validate_url("https://www.youtube.com/watch?v=test"))

    def test_validate_url_invalid_no_protocol(self):
        """Test validation of URL without protocol."""
        self.assertFalse(validate_url("www.youtube.com/watch?v=test"))

    def test_validate_url_invalid_short(self):
        """Test validation of very short URL."""
        self.assertFalse(validate_url("http://"))

    def test_validate_url_empty(self):
        """Test validation of empty URL."""
        self.assertFalse(validate_url(""))

    def test_validate_url_with_whitespace(self):
        """Test validation handles whitespace."""
        self.assertTrue(validate_url("   https://www.youtube.com/watch?v=test   "))

    def test_validate_proxy_empty(self):
        """Test that empty proxy is valid (no proxy)."""
        self.assertTrue(validate_proxy(""))

    def test_validate_proxy_valid_http(self):
        """Test valid HTTP proxy."""
        self.assertTrue(validate_proxy("http://proxy.example.com:8080"))

    def test_validate_proxy_valid_socks(self):
        """Test valid SOCKS proxy."""
        self.assertTrue(validate_proxy("socks5://proxy.example.com:1080"))

    def test_validate_proxy_invalid_no_port(self):
        """Test invalid proxy without port."""
        self.assertFalse(validate_proxy("http://proxy.example.com"))

    def test_validate_proxy_invalid_no_protocol(self):
        """Test invalid proxy without protocol."""
        self.assertFalse(validate_proxy("proxy.example.com:8080"))

    def test_validate_rate_limit_empty(self):
        """Test that empty rate limit is valid."""
        self.assertTrue(validate_rate_limit(""))

    def test_validate_rate_limit_kb(self):
        """Test valid kilobyte rate limit."""
        self.assertTrue(validate_rate_limit("50K"))

    def test_validate_rate_limit_mb(self):
        """Test valid megabyte rate limit."""
        self.assertTrue(validate_rate_limit("4.2M"))

    def test_validate_rate_limit_gb(self):
        """Test valid gigabyte rate limit."""
        self.assertTrue(validate_rate_limit("1.5G"))

    def test_validate_rate_limit_no_unit(self):
        """Test rate limit with no unit (bytes)."""
        self.assertTrue(validate_rate_limit("1024"))

    def test_validate_rate_limit_invalid_format(self):
        """Test invalid rate limit format."""
        self.assertFalse(validate_rate_limit("abc"))

    def test_validate_rate_limit_invalid_unit(self):
        """Test rate limit with invalid unit."""
        self.assertFalse(validate_rate_limit("50X"))

    def test_format_file_size_none(self):
        """Test file size formatting with None."""
        self.assertEqual(format_file_size(None), "N/A")

    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes."""
        self.assertEqual(format_file_size(512), "512.00 B")

    def test_format_file_size_kilobytes(self):
        """Test file size formatting for kilobytes."""
        result = format_file_size(1024 * 512)
        self.assertIn("KB", result)

    def test_format_file_size_megabytes(self):
        """Test file size formatting for megabytes."""
        result = format_file_size(1024 * 1024 * 100)
        self.assertIn("MB", result)

    def test_format_file_size_gigabytes(self):
        """Test file size formatting for gigabytes."""
        result = format_file_size(1024 * 1024 * 1024 * 5)
        self.assertIn("GB", result)

    def test_format_file_size_string_na(self):
        """Test file size formatting with 'N/A' string."""
        self.assertEqual(format_file_size("N/A"), "N/A")

    def test_format_file_size_invalid_type(self):
        """Test file size formatting with invalid type."""
        self.assertEqual(format_file_size("invalid"), "N/A")


class TestYTDownloaderGUI(unittest.TestCase):
    """Test cases for YTDownloaderGUI class."""

    def setUp(self):
        """Set up test fixtures."""
        self.root = tk.Tk()
        self.app = YTDownloaderGUI(self.root)

    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass

    def test_gui_initialization(self):
        """Test GUI initializes with correct default state."""
        self.assertEqual(self.app.title_label.cget("text"), "Title: N/A")
        self.assertEqual(self.app.duration_label.cget("text"), "Duration: N/A")
        self.assertEqual(self.app.status_label.cget("text"), "")
        self.assertEqual(self.app.progress_bar['value'], 0)
        self.assertEqual(len(self.app.download_queue), 0)

    def test_gui_has_all_tabs(self):
        """Test that all required tabs are present."""
        tabs = [self.app.notebook.tab(i, option='text') for i in range(self.app.notebook.index('end'))]
        required_tabs = ['Video', 'Audio', 'Subtitles', 'Playlist', 'Chapters', 'Settings', 'Downloads']
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
        self.assertEqual(self.app.title_label.cget("text"), "Title: N/A")
        self.assertEqual(self.app.progress_bar['value'], 0)

    @patch('main.messagebox.showwarning')
    def test_fetch_info_empty_url(self, mock_warning):
        """Test fetch_info with empty URL shows warning."""
        self.app.url_entry.delete(0, tk.END)
        self.app.fetch_info()
        mock_warning.assert_called_once()

    @patch('main.messagebox.showwarning')
    def test_fetch_info_invalid_url(self, mock_warning):
        """Test fetch_info with invalid URL shows warning."""
        self.app.url_entry.insert(0, "invalid url")
        self.app.fetch_info()
        mock_warning.assert_called_once()

    @patch('main.messagebox.showwarning')
    def test_add_to_queue_empty_url(self, mock_warning):
        """Test add_to_queue with empty URL shows warning."""
        self.app.url_entry.delete(0, tk.END)
        self.app.add_to_queue()
        mock_warning.assert_called()

    @patch('main.messagebox.showwarning')
    def test_add_to_queue_no_format(self, mock_warning):
        """Test add_to_queue with no format selected shows warning."""
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.video_format_var.set("")
        self.app.add_to_queue()
        mock_warning.assert_called()

    @patch('main.messagebox.showerror')
    def test_add_to_queue_invalid_proxy(self, mock_error):
        """Test add_to_queue with invalid proxy shows error."""
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.video_format_var.set("1920x1080")
        self.app.proxy_entry.insert(0, "invalid_proxy")
        self.app.add_to_queue()
        mock_error.assert_called()

    @patch('main.messagebox.showerror')
    def test_add_to_queue_invalid_rate_limit(self, mock_error):
        """Test add_to_queue with invalid rate limit shows error."""
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.video_format_var.set("1920x1080")
        self.app.ratelimit_entry.insert(0, "invalid_rate")
        self.app.add_to_queue()
        mock_error.assert_called()

    @patch('main.messagebox.showerror')
    def test_add_to_queue_invalid_path(self, mock_error):
        """Test add_to_queue with non-existent path shows error."""
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.video_format_var.set("1920x1080")
        self.app.path_entry.insert(0, "/nonexistent/path/that/does/not/exist")
        self.app.add_to_queue()
        mock_error.assert_called()

    def test_add_to_queue_success(self):
        """Test successful addition to queue."""
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.video_format_var.set("1920x1080 - 22")
        self.app.path_entry.delete(0, tk.END)
        self.app.path_entry.insert(0, ".")

        self.app.add_to_queue()

        self.assertEqual(len(self.app.download_queue), 1)
        self.assertEqual(self.app.download_queue[0]['url'], "https://www.youtube.com/watch?v=test")

    def test_is_downloading(self):
        """Test is_downloading detection."""
        self.assertFalse(self.app.is_downloading())

        # Add downloading item
        self.app.download_queue.append({'status': 'Queued', 'url': 'test'})
        self.assertFalse(self.app.is_downloading())

        # Change to downloading
        self.app.download_queue[0]['status'] = 'Downloading'
        self.assertTrue(self.app.is_downloading())

    def test_cancel_token_initialization(self):
        """Test that cancel token is properly initialized and used."""
        self.assertIsNone(self.app.cancel_token)

    def test_process_ui_queue_empty(self):
        """Test process_ui_queue with empty queue."""
        # Should not raise any exception
        self.app.process_ui_queue()

    def test_process_ui_queue_with_task(self):
        """Test process_ui_queue executes queued tasks."""
        mock_func = MagicMock()
        self.app.ui_queue.put((mock_func, {'key': 'value'}))
        self.app.process_ui_queue()
        mock_func.assert_called_once_with(key='value')

    def test_toggle_theme(self):
        """Test theme toggle."""
        initial_dark_mode = self.app.dark_mode.get()
        self.app.toggle_theme()
        self.assertNotEqual(self.app.dark_mode.get(), initial_dark_mode)

    @patch('main.messagebox.showwarning')
    def test_remove_from_queue_no_selection(self, mock_warning):
        """Test remove_from_queue with no selection."""
        self.app.remove_from_queue()
        mock_warning.assert_called()

    def test_remove_from_queue_success(self):
        """Test successful removal from queue."""
        self.app.download_queue.append({'url': 'test1', 'status': 'Queued'})
        self.app.download_queue.append({'url': 'test2', 'status': 'Queued'})
        self.app.update_download_queue_list()

        # Select first item
        self.app.download_queue_tree.selection_set(self.app.download_queue_tree.get_children()[0])
        self.app.remove_from_queue()

        self.assertEqual(len(self.app.download_queue), 1)
        self.assertEqual(self.app.download_queue[0]['url'], 'test2')

    @patch('main.messagebox.showwarning')
    def test_cancel_download_item_no_selection(self, mock_warning):
        """Test cancel_download_item with no selection."""
        self.app.cancel_download_item()
        mock_warning.assert_called()

    def test_cancel_download_item_success(self):
        """Test successful cancellation of queued item."""
        self.app.download_queue.append({'url': 'test', 'status': 'Queued'})
        self.app.update_download_queue_list()

        # Select item
        self.app.download_queue_tree.selection_set(self.app.download_queue_tree.get_children()[0])
        self.app.cancel_download_item()

        self.assertEqual(self.app.download_queue[0]['status'], 'Cancelled')

    @patch('main.messagebox.showwarning')
    def test_open_file_location_no_selection(self, mock_warning):
        """Test open_file_location with no selection."""
        self.app.open_file_location()
        mock_warning.assert_called()

    def test_update_download_queue_list(self):
        """Test download queue list is properly updated."""
        self.app.download_queue.append({
            'url': 'https://example.com/video1',
            'status': 'Queued',
            'size': '100 MB',
            'speed': 'N/A',
            'eta': 'N/A'
        })
        self.app.download_queue.append({
            'url': 'https://example.com/video2',
            'status': 'Downloading',
            'size': '200 MB',
            'speed': '1 MB/s',
            'eta': '3:00'
        })

        self.app.update_download_queue_list()

        items = self.app.download_queue_tree.get_children()
        self.assertEqual(len(items), 2)

    def test_extract_format_id(self):
        """Test format ID extraction."""
        format_str = "1920x1080@30fps (MP4) - V:avc1 A:mp4a (500.00 MB) - 22"
        format_id = self.app._extract_format_id(format_str)
        self.assertEqual(format_id, "22")

    def test_extract_format_id_empty_string(self):
        """Test format ID extraction with empty string."""
        format_id = self.app._extract_format_id("")
        self.assertIsNone(format_id)

    def test_extract_format_id_no_separator(self):
        """Test format ID extraction without separator."""
        format_str = "1920x1080"
        format_id = self.app._extract_format_id(format_str)
        self.assertEqual(format_id, "1920x1080")

    def test_pause_button_states(self):
        """Test pause button state changes."""
        self.assertEqual(str(self.app.pause_button.cget('state')), 'disabled')

        # When download starts, pause should be enabled
        self.app.pause_button.config(state='normal')
        self.assertEqual(str(self.app.pause_button.cget('state')), 'normal')


class TestGUIErrorHandling(unittest.TestCase):
    """Test cases for GUI error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.root = tk.Tk()
        self.app = YTDownloaderGUI(self.root)

    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass

    @patch('main.messagebox.showerror')
    def test_handle_error(self, mock_error_dialog):
        """Test error handling and display."""
        test_error = ValueError("Test error message")
        self.app.handle_error("Test error occurred", test_error)
        mock_error_dialog.assert_called_once()


if __name__ == '__main__':
    unittest.main()
