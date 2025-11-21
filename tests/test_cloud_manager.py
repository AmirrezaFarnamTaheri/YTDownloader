import unittest
import os
from unittest.mock import patch, MagicMock
from cloud_manager import CloudManager

class TestCloudManager(unittest.TestCase):

    def test_upload_file_not_found(self):
        cm = CloudManager()
        with self.assertRaises(FileNotFoundError):
            cm.upload_file("non_existent_file.txt")

    def test_upload_unsupported_provider(self):
        # Create a dummy file
        with open("dummy.txt", "w") as f:
            f.write("test")

        cm = CloudManager()
        try:
            with self.assertRaises(NotImplementedError):
                cm.upload_file("dummy.txt", provider="dropbox")
        finally:
            if os.path.exists("dummy.txt"):
                os.remove("dummy.txt")

    @patch('os.path.exists')
    def test_upload_google_drive_missing_creds(self, mock_exists):
        # Mock file exists check to return True for file_path, False for credentials
        def side_effect(path):
            if path == "dummy.txt": return True
            if path == "client_secrets.json": return False
            return False
        mock_exists.side_effect = side_effect

        cm = CloudManager()
        with self.assertRaisesRegex(Exception, "Google Drive not configured"):
             cm.upload_file("dummy.txt", provider="google_drive")

    @patch('os.path.exists')
    @patch('pydrive2.auth.GoogleAuth')
    @patch('pydrive2.drive.GoogleDrive')
    def test_upload_to_google_drive_success(self, MockGoogleDrive, MockGoogleAuth, mock_exists):
         # Mock file exists for everything
         mock_exists.return_value = True

         mock_gauth = MockGoogleAuth.return_value
         mock_gauth.credentials = MagicMock()
         mock_gauth.access_token_expired = False

         mock_drive = MockGoogleDrive.return_value
         mock_file = MagicMock()
         mock_drive.CreateFile.return_value = mock_file

         cm = CloudManager()
         cm.upload_file("dummy.txt", provider="google_drive")

         mock_drive.CreateFile.assert_called()
         mock_file.SetContentFile.assert_called_with("dummy.txt")
         mock_file.Upload.assert_called()
