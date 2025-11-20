import unittest
from unittest.mock import patch, MagicMock, ANY
import tkinter as tk
from main import YTDownloaderGUI
import queue

class TestMainInteractions(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = YTDownloaderGUI(self.root)
        # Disable queue polling for tests to avoid thread issues
        self.root.after_cancel(self.app.master.after(1000, self.app.check_clipboard))

    def tearDown(self):
        try:
            self.root.destroy()
        except:
            pass

    @patch('main.sv_ttk.toggle_theme')
    @patch('main.ConfigManager.save_config')
    def test_toggle_theme(self, mock_save, mock_toggle):
        initial_mode = self.app.dark_mode.get()
        self.app.toggle_theme()
        self.assertNotEqual(self.app.dark_mode.get(), initial_mode)
        mock_toggle.assert_called_once()
        mock_save.assert_called()

    @patch('main.get_video_info')
    def test_fetch_info_success(self, mock_get_info):
        # Mock info
        mock_get_info.return_value = {
            'title': 'Test Video',
            'duration': '10:00',
            'video_streams': [{'resolution': '1080p', 'fps': 60, 'ext': 'mp4', 'format_id': '137'}],
            'audio_streams': [{'abr': 128, 'ext': 'm4a', 'format_id': '140'}],
            'subtitles': {'en': 'English'},
            'thumbnail': 'http://thumb.jpg'
        }
        self.app.url_entry.insert(0, "http://youtube.com/watch?v=123")

        # Mock requests for thumbnail
        with patch('main.requests.get') as mock_req:
            mock_req.return_value.content = b'fakeimage'
            mock_req.return_value.raise_for_status = MagicMock()

            # Start fetch
            self.app.fetch_info()

            # Since fetch_info runs in a thread, we join it if we can access it,
            # but the app doesn't expose the thread handle easily in the original code (it was self.fetch_thread).
            if self.app.fetch_thread:
                self.app.fetch_thread.join()

            # Process queue
            self.app.process_ui_queue()

            self.assertEqual(self.app.title_label.cget('text'), "Test Video")
            self.assertIn("10:00", self.app.duration_label.cget('text'))
            self.assertEqual(self.app.subtitle_lang_menu['values'], ('en',))

    @patch('main.download_video')
    def test_download_execution(self, mock_download):
        # Setup an item with all required keys
        self.app.download_queue.append({
            'url': 'http://test',
            'status': 'Queued',
            'video_format': 'best',
            'audio_format': 'best',
            'subtitle_lang': None,
            'subtitle_format': 'srt',
            'output_path': '/tmp',
            'playlist': False,
            'split_chapters': False,
            'proxy': None,
            'rate_limit': None,
            'cookies_browser': None,
            'cookies_profile': None,
            'download_sections': None,
            'add_metadata': False,
            'embed_thumbnail': False,
            'size': '0',
            'speed': '0'
        })

        # Trigger processing
        self.app.process_download_queue()

        # Check if thread started
        # We need to join the download thread.
        # YTDownloaderGUI.download is the target.
        # Since we cannot easily join the specific thread created inside start_download_thread (local var),
        # we might need to verify side effects or wait.
        # However, we mocked download_video.

        # Wait a bit for thread to run
        import time
        time.sleep(0.1)
        self.app.process_ui_queue()

        mock_download.assert_called()
        self.assertEqual(self.app.download_queue[0]['status'], 'Completed')

    @patch('main.YTDownloaderGUI.start_download_thread')
    @patch('main.filedialog.askopenfilename')
    def test_import_urls(self, mock_ask, mock_start_thread):
        # Mock file content
        with patch('builtins.open', unittest.mock.mock_open(read_data="http://test1.com\nhttp://test2.com")):
            mock_ask.return_value = "list.txt"
            self.app.import_urls_from_file()

            self.assertEqual(len(self.app.download_queue), 2)
            self.assertEqual(self.app.download_queue[0]['url'], "http://test1.com")

    def test_change_language(self):
        with patch('main.ConfigManager.save_config') as mock_save:
            self.app.lang_var.set("es")
            self.app.change_language()
            mock_save.assert_called()
            self.assertEqual(self.app.config['language'], 'es')

    @patch('main.HistoryManager.get_history')
    def test_load_history(self, mock_get):
        mock_get.return_value = [{'title': 'H1', 'status': 'Completed', 'timestamp': '2023-01-01'}]
        self.app.load_history()
        children = self.app.history_tree.get_children()
        self.assertEqual(len(children), 1)
        item = self.app.history_tree.item(children[0])
        self.assertEqual(item['values'][0], 'H1')

    @patch('main.os.startfile', create=True)
    @patch('main.sys')
    def test_play_history_item(self, mock_sys, mock_start):
        mock_sys.platform = 'win32'
        # Setup history
        self.app._history_data = [{'file_path': '/tmp/vid.mp4'}]
        # Mock selection
        self.app.history_tree.insert("", "end", iid=0, values=('T',))
        self.app.history_tree.selection_set(0)

        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.app.play_history_item()
            mock_start.assert_called_with('/tmp/vid.mp4')
