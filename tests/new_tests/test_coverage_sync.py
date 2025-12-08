
import unittest
from unittest.mock import MagicMock, patch
import os
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
        mock_walk.return_value = [
            ("/root", [], ["file1.txt"])
        ]

        # Mock cloud upload
        self.mock_cloud.upload_file.return_value = "file_id"

        res = self.manager.export_data()
        self.assertTrue(res)
        MockZip.assert_called()
        self.mock_cloud.upload_file.assert_called()

    @patch("zipfile.ZipFile")
    def test_export_data_fail(self, MockZip):
        self.mock_cloud.upload_file.side_effect = Exception("Upload failed")
        res = self.manager.export_data()
        self.assertFalse(res)

    @patch("zipfile.ZipFile")
    @patch("os.path.exists")
    def test_import_data_success(self, mock_exists, MockZip):
        # Mock download
        self.mock_cloud.download_file.return_value = True
        mock_exists.return_value = True # Backup file exists

        res = self.manager.import_data("file_id")
        self.assertTrue(res)
        MockZip.assert_called()
        # Should extract
        MockZip.return_value.__enter__.return_value.extractall.assert_called()

    def test_import_data_fail_download(self):
        self.mock_cloud.download_file.return_value = False
        res = self.manager.import_data("file_id")
        self.assertFalse(res)
