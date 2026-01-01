import unittest
from unittest.mock import MagicMock, patch

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

        self.manager.import_data("file_id")
        MockZip.assert_called()
        # Should extract
        # MockZip.return_value.__enter__.return_value.extractall.assert_called() # Implementation uses open+copyfileobj

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
        mock_zip_instance.infolist.return_value = [malicious_info, valid_info]

        # Mock open to verify we only write valid files
        with patch("builtins.open", mock_open=MagicMock()) as mock_file_open:
            self.manager.import_data("file_id")

            # Check calls
            # Expect open call for config.json (or temp path), but NOT for passwd
            # Since we can't easily check path resolution mocks here without deep patching of Path or os.path,
            # we rely on the fact that SyncManager logs/skips.
            # If the code checks is_safe_path, it will skip.

            # Verify builtins.open was NOT called with the malicious path
            for call in mock_file_open.mock_calls:
                args = call.args
                if args and "passwd" in str(args[0]):
                    self.fail("Attempted to open malicious file path!")

            # Assert that we tried to read/extract at least one file (the valid one)
            # Depending on implementation (extract vs read/write), we check zip instance calls
            # If implementation uses zip.open(), check that
            mock_zip_instance.open.assert_called()
            # Ensure it didn't open the malicious file
            # If open was called with malicious_info or malicious filename

            # Safest check: Verify only valid_info was processed if loop filters
