import unittest
import json
from unittest.mock import MagicMock, patch, mock_open

from sync_manager import SyncManager


class TestSyncManager(unittest.TestCase):
    def setUp(self):
        self.mock_cloud = MagicMock()
        self.mock_config = MagicMock()
        self.manager = SyncManager(self.mock_cloud, self.mock_config)

    @patch("zipfile.ZipFile")
    @patch("os.walk")
    def test_export_data_success(self, mock_walk, MockZip):
        # Mock file system
        mock_walk.return_value = [("/root", [], ["file1.txt"])]

        # Mock cloud upload
        self.mock_cloud.upload_file.return_value = "file_id"

        self.manager.export_data("backup.zip")
        MockZip.assert_called()

    @patch("zipfile.ZipFile")
    def test_export_data_fail(self, MockZip):
        MockZip.side_effect = OSError("Write Error")
        with self.assertRaises(OSError):
            self.manager.export_data("backup.zip")

    @patch("zipfile.ZipFile")
    @patch("os.path.exists")
    def test_import_data_success(self, mock_exists, MockZip):
        # Mock download
        self.mock_cloud.download_file.return_value = True
        mock_exists.return_value = True  # Backup file exists

        # Setup ZipFile mock with infolist
        mock_zip_instance = MockZip.return_value.__enter__.return_value
        config_info = MagicMock()
        config_info.filename = "config.json"
        mock_zip_instance.infolist.return_value = [config_info]

        # Setup open context for config.json
        mock_file = MagicMock()
        # json.load needs read() to return bytes or str
        mock_file.read.return_value = b'{"theme": "dark"}'
        mock_zip_instance.open.return_value.__enter__.return_value = mock_file

        self.manager.import_data("file_id")
        MockZip.assert_called()
        self.mock_config.save_config.assert_called()

    @patch("os.path.exists")
    def test_import_data_not_found(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            self.manager.import_data("file_id")

    @patch("zipfile.ZipFile")
    @patch("os.path.exists")
    def test_import_data_zip_slip(self, mock_exists, MockZip):
        """Test prevention of Zip Slip vulnerability."""
        self.mock_cloud.download_file.return_value = True
        mock_exists.return_value = True

        # Create a malicious mock zip info
        malicious_info = MagicMock()
        malicious_info.filename = "../../../etc/passwd"

        # Create a valid mock zip info
        valid_info = MagicMock()
        valid_info.filename = "config.json"

        mock_zip_instance = MockZip.return_value.__enter__.return_value
        # Order: Malicious first, then valid
        mock_zip_instance.infolist.return_value = [malicious_info, valid_info]

        # Configure file reading
        mock_file = MagicMock()
        mock_file.read.return_value = b'{"theme": "dark"}'

        # Mock the context manager for zip.open()
        mock_zip_instance.open.return_value.__enter__.return_value = mock_file

        self.manager.import_data("file_id")

        # Assertions
        # 1. Verify malicious file was NOT opened
        # We can check call args of open
        # MockZip.open calls
        open_calls = mock_zip_instance.open.call_args_list
        for call in open_calls:
            filename = call[0][0]
            if "passwd" in filename:
                self.fail("Attempted to open malicious file path!")

        # 2. Verify valid file WAS opened
        mock_zip_instance.open.assert_called_with("config.json")
