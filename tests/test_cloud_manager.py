import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
from cloud_manager import CloudManager


class TestCloudManager(unittest.TestCase):

    def setUp(self):
        self.manager = CloudManager()

    def test_upload_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.upload_file("non_existent_file.txt")

    @patch("os.path.exists")
    def test_upload_file_unsupported_provider(self, mock_exists):
        mock_exists.return_value = True
        with self.assertRaises(NotImplementedError):
            self.manager.upload_file("test.txt", provider="dropbox")

    @patch("os.path.exists")
    def test_upload_google_drive_missing_secrets(self, mock_exists):
        # Mock file exists for the file to upload, but return False for secrets
        def side_effect(path):
            if path == "test.txt":
                return True
            if path == "client_secrets.json":
                return False
            return False

        mock_exists.side_effect = side_effect

        with self.assertRaisesRegex(Exception, "Google Drive not configured"):
            self.manager.upload_file("test.txt", provider="google_drive")

    @patch("os.path.exists")
    @patch.dict(
        "sys.modules", {"pydrive2.auth": MagicMock(), "pydrive2.drive": MagicMock()}
    )
    def test_upload_google_drive_success(self, mock_exists):
        mock_exists.return_value = True

        with patch("pydrive2.auth.GoogleAuth") as MockAuth, patch(
            "pydrive2.drive.GoogleDrive"
        ) as MockDrive:

            mock_gauth = MockAuth.return_value
            mock_gauth.credentials = MagicMock()  # Simulate credentials exist
            mock_gauth.access_token_expired = False

            mock_drive_instance = MockDrive.return_value
            mock_file = MagicMock()
            mock_drive_instance.CreateFile.return_value = mock_file

            self.manager.upload_file("test.txt", provider="google_drive")

            mock_gauth.Authorize.assert_called()
            mock_drive_instance.CreateFile.assert_called_with({"title": "test.txt"})
            mock_file.SetContentFile.assert_called_with("test.txt")
            mock_file.Upload.assert_called()

    @patch("os.path.exists")
    @patch.dict(
        "sys.modules", {"pydrive2.auth": MagicMock(), "pydrive2.drive": MagicMock()}
    )
    def test_upload_google_drive_refresh_token(self, mock_exists):
        mock_exists.return_value = True

        with patch("pydrive2.auth.GoogleAuth") as MockAuth, patch(
            "pydrive2.drive.GoogleDrive"
        ) as MockDrive:

            mock_gauth = MockAuth.return_value
            mock_gauth.credentials = MagicMock()
            mock_gauth.access_token_expired = True

            self.manager.upload_file("test.txt")

            mock_gauth.Refresh.assert_called()

    @patch("os.path.exists")
    @patch.dict(
        "sys.modules", {"pydrive2.auth": MagicMock(), "pydrive2.drive": MagicMock()}
    )
    def test_upload_google_drive_no_creds_headless(self, mock_exists):
        mock_exists.return_value = True

        with patch("pydrive2.auth.GoogleAuth") as MockAuth, patch.dict(
            os.environ, {"HEADLESS_MODE": "1"}
        ):

            mock_gauth = MockAuth.return_value
            mock_gauth.credentials = None

            with self.assertRaisesRegex(
                Exception, "Cannot authenticate in headless mode"
            ):
                self.manager.upload_file("test.txt")

    @patch("os.path.exists")
    @patch.dict(
        "sys.modules", {"pydrive2.auth": MagicMock(), "pydrive2.drive": MagicMock()}
    )
    def test_upload_google_drive_no_creds_interactive(self, mock_exists):
        mock_exists.return_value = True

        with patch("pydrive2.auth.GoogleAuth") as MockAuth, patch(
            "pydrive2.drive.GoogleDrive"
        ) as MockDrive:

            mock_gauth = MockAuth.return_value
            mock_gauth.credentials = None

            # Assume not headless
            if "HEADLESS_MODE" in os.environ:
                del os.environ["HEADLESS_MODE"]

            self.manager.upload_file("test.txt")

            mock_gauth.LocalWebserverAuth.assert_called()

    @patch("os.path.exists")
    def test_upload_google_drive_import_error(self, mock_exists):
        mock_exists.return_value = True
        # Simulate import error
        with patch.dict("sys.modules", {"pydrive2.auth": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                with self.assertRaisesRegex(Exception, "PyDrive2 dependency missing"):
                    self.manager.upload_file("test.txt")

    @patch("os.path.exists")
    @patch.dict(
        "sys.modules", {"pydrive2.auth": MagicMock(), "pydrive2.drive": MagicMock()}
    )
    def test_upload_google_drive_general_exception(self, mock_exists):
        mock_exists.return_value = True

        with patch("pydrive2.auth.GoogleAuth") as MockAuth:
            mock_gauth = MockAuth.return_value
            # We need to make sure we are not failing on the check for access_token_expired
            # The code path is:
            # 1. gauth = GoogleAuth()
            # 2. LoadCredentialsFile
            # 3. Check credentials is None?

            # Let's mock such that we have credentials, but Authorize fails.
            mock_gauth.credentials = MagicMock()
            mock_gauth.access_token_expired = False

            mock_gauth.Authorize.side_effect = Exception("Auth failed")

            with self.assertRaisesRegex(Exception, "Auth failed"):
                self.manager.upload_file("test.txt")
