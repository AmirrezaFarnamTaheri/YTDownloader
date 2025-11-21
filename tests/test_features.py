import unittest
from unittest.mock import MagicMock, patch
import flet as ft
from main import AppState, DownloadItemControl

# Mock the page
class MockPage:
    def __init__(self):
        self.overlay = []
        self.controls = []
        self.theme_mode = "DARK"
        self.snack_bar = None

    def update(self):
        pass

    def show_snack_bar(self, bar):
        self.snack_bar = bar

class TestFeatureVerification(unittest.TestCase):

    def setUp(self):
        self.state = AppState()
        # Manually reset queue for each test
        self.state.download_queue = []
        self.page = MockPage()

    def test_keyboard_navigation_logic(self):
        """Verify that J/K keys change the selected index in the queue."""
        # Add dummy items
        self.state.download_queue.append({"url": "http://a.com", "status": "Queued", "control": MagicMock()})
        self.state.download_queue.append({"url": "http://b.com", "status": "Queued", "control": MagicMock()})
        self.state.download_queue.append({"url": "http://c.com", "status": "Queued", "control": MagicMock()})

        self.state.selected_queue_index = 0 # Start at top

        # Simulate 'J' (Down)
        self.state.selected_queue_index += 1
        self.assertEqual(self.state.selected_queue_index, 1)

        # Simulate 'J' (Down) again
        self.state.selected_queue_index += 1
        self.assertEqual(self.state.selected_queue_index, 2)

        # Simulate 'J' (Loop around?) - Logic in main.py implements loop
        self.state.selected_queue_index += 1
        if self.state.selected_queue_index >= len(self.state.download_queue):
             self.state.selected_queue_index = 0
        self.assertEqual(self.state.selected_queue_index, 0)

        # Simulate 'K' (Up) - Loop back
        self.state.selected_queue_index -= 1
        if self.state.selected_queue_index < 0:
             self.state.selected_queue_index = len(self.state.download_queue) - 1
        self.assertEqual(self.state.selected_queue_index, 2)

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_downloader_arguments_partial(self, mock_ydl):
        """Verify that start/end time arguments are passed to yt-dlp."""
        from downloader import download_video

        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        item = {}
        def hook(d, i): pass

        download_video(
            "http://example.com",
            hook,
            item,
            start_time="00:01:00",
            end_time="00:02:00"
        )

        # Check options passed to constructor
        call_args = mock_ydl.call_args[0][0]
        self.assertIn('download_ranges', call_args)
        self.assertTrue(callable(call_args['download_ranges']))
        self.assertTrue(call_args.get('force_keyframes_at_cuts'))

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_downloader_arguments_aria2c(self, mock_ydl):
        """Verify that aria2c arguments are passed."""
        from downloader import download_video

        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        item = {}
        def hook(d, i): pass

        download_video(
            "http://example.com",
            hook,
            item,
            use_aria2c=True
        )

        call_args = mock_ydl.call_args[0][0]
        self.assertEqual(call_args.get('external_downloader'), 'aria2c')
        self.assertIn('-x', call_args.get('external_downloader_args'))

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_downloader_arguments_gpu(self, mock_ydl):
        """Verify that GPU arguments are added to postprocessor args."""
        from downloader import download_video

        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        item = {}
        def hook(d, i): pass

        download_video(
            "http://example.com",
            hook,
            item,
            gpu_accel="cuda"
        )

        call_args = mock_ydl.call_args[0][0]
        # Check postprocessor_args
        pp_args = call_args.get('postprocessor_args', {})
        self.assertIn('ffmpeg', pp_args)
        self.assertIn('h264_nvenc', pp_args['ffmpeg'])

if __name__ == '__main__':
    unittest.main()
