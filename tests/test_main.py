import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import AppState, DownloadItemControl, CancelToken
from cloud_manager import CloudManager

class TestMain(unittest.TestCase):
    def setUp(self):
        self.app_state = AppState()

    def test_app_state_initialization(self):
        self.assertIsInstance(self.app_state.download_queue, list)
        self.assertIsInstance(self.app_state.history, list)
        self.assertFalse(self.app_state.is_paused)
        self.assertIsInstance(self.app_state.cloud_manager, CloudManager)
        self.assertIsNone(self.app_state.scheduled_time)

    @patch('main.ft.Card')
    @patch('main.ft.Container')
    @patch('main.ft.Column')
    @patch('main.ft.Row')
    @patch('main.ft.Text')
    @patch('main.ft.ProgressBar')
    @patch('main.ft.IconButton')
    def test_download_item_control(self, mock_icon, mock_pb, mock_txt, mock_row, mock_col, mock_cont, mock_card):
        # Ensure ft.Text returns a new Mock each time so status_text and details_text are different
        mock_txt.side_effect = lambda *args, **kwargs: MagicMock()

        item = {'url': 'http://test', 'status': 'Queued'}
        on_cancel = MagicMock()
        on_remove = MagicMock()
        on_reorder = MagicMock()

        control = DownloadItemControl(item, on_cancel, on_remove, on_reorder)
        control.build()

        control.update_progress()

        self.assertEqual(control.status_text.value, 'Queued')
        self.assertEqual(control.details_text.value, 'N/A | N/A | ETA: N/A')

    def test_cancel_token(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        token.cancel()
        self.assertTrue(token.cancelled)

        with self.assertRaisesRegex(Exception, "Download cancelled by user"):
            token.check({})

    def test_cancel_token_pause(self):
        token = CancelToken()
        token.pause()
        self.assertTrue(token.is_paused)
        token.resume()
        self.assertFalse(token.is_paused)

class TestCloudManager(unittest.TestCase):
    def test_upload_file_not_found(self):
        cm = CloudManager()
        with self.assertRaises(FileNotFoundError):
            cm.upload_file("non_existent_file.txt")

    def test_upload_file_no_credentials(self):
        cm = CloudManager()
        # Create dummy file
        with open("test_upload.txt", "w") as f:
            f.write("test")

        try:
            with self.assertRaisesRegex(Exception, "credentials not configured"):
                cm.upload_file("test_upload.txt")
        finally:
            if os.path.exists("test_upload.txt"):
                os.remove("test_upload.txt")

if __name__ == '__main__':
    unittest.main()
