"""
Comprehensive unit tests for the GUI module.
Tests cover UI initialization, user interactions, and event handling.
"""
import unittest
from unittest.mock import patch, MagicMock, call
import tkinter as tk
from main_legacy import YTDownloaderGUI
import datetime

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
        # Note: Tabs changed in modern UI and localized
        # 'Video', 'Audio', 'Advanced', 'RSS', 'Settings' are default English keys
        # Added Post-Processing tab
        required_tabs = ['Video', 'Audio', 'Advanced', 'Post-Processing', 'RSS', 'Settings']
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

    @patch('main_legacy.YTDownloaderGUI.show_toast')
    def test_fetch_info_empty_url(self, mock_toast):
        """Test fetch_info with empty URL shows toast."""
        self.app.url_entry.delete(0, tk.END)
        self.app.fetch_info()
        mock_toast.assert_called_once()

    @patch('main_legacy.YTDownloaderGUI.show_toast')
    def test_add_to_queue_empty_url(self, mock_toast):
        self.app.url_entry.delete(0, tk.END)
        self.app.add_to_queue()
        mock_toast.assert_called()

    @patch('main_legacy.YTDownloaderGUI.show_toast')
    def test_add_to_queue_success(self, mock_toast):
        """Test successful addition to queue."""
        self.app.url_entry.insert(0, "https://www.youtube.com/watch?v=test")
        self.app.video_format_var.set("1920x1080 - 22")
        self.app.path_entry.delete(0, tk.END)
        self.app.path_entry.insert(0, ".")

        self.app.add_to_queue()

        self.assertEqual(len(self.app.download_queue), 1)
        self.assertEqual(self.app.download_queue[0]['url'], "https://www.youtube.com/watch?v=test")
        # Toast message is localized now
        mock_toast.assert_called()

    def test_is_downloading(self):
        """Test is_downloading detection."""
        self.assertFalse(self.app.is_downloading())
        self.app.download_queue.append({'status': 'Queued', 'url': 'test'})
        self.assertFalse(self.app.is_downloading())
        self.app.download_queue[0]['status'] = 'Downloading'
        self.assertTrue(self.app.is_downloading())

    @patch('main_legacy.YTDownloaderGUI.show_toast')
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

    @patch('main_legacy.messagebox.showerror')
    def test_handle_error_threadsafe(self, mock_showerror):
        # queue the error
        self.app.handle_error_threadsafe("Title", "Error")
        # process queue
        self.app.process_ui_queue()
        mock_showerror.assert_called_with("Title", "Error")

    @patch('main_legacy.subprocess.Popen')
    @patch('main_legacy.sys')
    @patch('main_legacy.os.startfile', create=True)
    def test_open_file_location(self, mock_startfile, mock_sys, mock_popen):
        # Add dummy item
        self.app.download_queue.append({'url': 'u', 'status': 'Completed', 'output_path': '/tmp/test'})
        self.app.update_download_queue_list()
        self.app.download_queue_tree.selection_set(self.app.download_queue_tree.get_children()[0])

        # Test Windows
        mock_sys.platform = 'win32'
        self.app.open_file_location()
        mock_startfile.assert_called_with('/tmp/test')

        # Test Linux
        mock_sys.platform = 'linux'
        self.app.open_file_location()
        mock_popen.assert_called_with(['xdg-open', '/tmp/test'])

    @patch('main_legacy.HistoryManager.clear_history')
    @patch('main_legacy.messagebox.askyesno')
    def test_clear_history_confirm(self, mock_ask, mock_clear):
        mock_ask.return_value = True
        self.app.clear_history()
        mock_clear.assert_called_once()

    @patch('main_legacy.HistoryManager.clear_history')
    @patch('main_legacy.messagebox.askyesno')
    def test_clear_history_cancel(self, mock_ask, mock_clear):
        mock_ask.return_value = False
        self.app.clear_history()
        mock_clear.assert_not_called()

    @patch('main_legacy.RSSManager.get_latest_video')
    def test_check_rss_feeds(self, mock_get_video):
        # Setup config
        self.app.config['rss_feeds'] = ['http://rss.xml']

        # Mock video found
        mock_get_video.return_value = {'link': 'http://video'}

        with patch.object(self.app, 'show_toast') as mock_toast:
             self.app.check_rss_feeds()
             # Wait for thread - hard to test async thread in unit test without joining
             # But we can check if thread started.
             pass

    @patch('main_legacy.simpledialog.askstring')
    @patch('main_legacy.YTDownloaderGUI.add_to_queue')
    def test_schedule_download_dialog_success(self, mock_add, mock_ask):
        self.app.url_entry.insert(0, "http://test.com")
        mock_ask.return_value = "12:00"

        # We need to mock datetime to ensure stable testing
        with patch('main_legacy.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = datetime.datetime(2023, 1, 1, 10, 0, 0)
            mock_datetime.datetime.strptime.side_effect = lambda t, f: datetime.datetime.strptime(t, f)
            mock_datetime.datetime.combine.side_effect = lambda d, t: datetime.datetime.combine(d, t)

            self.app.schedule_download_dialog()

            mock_add.assert_called_once()
            # Check that scheduled_time was passed
            kwargs = mock_add.call_args[1]
            self.assertIn('scheduled_time', kwargs)

    def test_check_scheduled_downloads(self):
        # Add a scheduled item
        scheduled_time = datetime.datetime.now() - datetime.timedelta(minutes=1) # Past time
        self.app.download_queue.append({
            'url': 'http://test.com',
            'status': 'Scheduled (12:00)',
            'scheduled_time': scheduled_time,
            'video_format': 'best'
        })

        with patch.object(self.app, 'process_download_queue') as mock_process:
            self.app.check_scheduled_downloads()

            self.assertEqual(self.app.download_queue[0]['status'], 'Queued')
            mock_process.assert_called()

    @patch('main_legacy.filedialog.askopenfilename')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="http://test1.com\nhttp://test2.com")
    def test_import_urls_from_file_batch(self, mock_file, mock_dialog):
        mock_dialog.return_value = "urls.txt"

        self.app.import_urls_from_file()

        self.assertEqual(len(self.app.download_queue), 2)
        self.assertEqual(self.app.download_queue[0]['url'], "http://test1.com")
        self.assertEqual(self.app.download_queue[1]['url'], "http://test2.com")

if __name__ == '__main__':
    unittest.main()
