# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import os
import unittest
from unittest.mock import MagicMock, patch

from cloud_manager import CloudManager


class TestCloudManagerPatched(unittest.TestCase):
    def setUp(self):
        self.manager = CloudManager()

    @patch("os.path.exists")
    def test_upload_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            self.manager.upload_file("non_existent_file.txt")

    @patch("os.path.exists")
    def test_upload_file_unsupported_provider(self, mock_exists):
        mock_exists.return_value = True
        with self.assertRaises(NotImplementedError):
            self.manager.upload_file("test.txt", provider="dropbox")

    @patch("os.path.exists")
    def test_upload_google_drive_missing_secrets(self, mock_exists):
        # File exists, but client_secrets.json does not
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
    @patch("pydrive2.auth.GoogleAuth")
    @patch("pydrive2.drive.GoogleDrive")
    def test_upload_google_drive_success(self, MockDrive, MockAuth, mock_exists):
        def side_effect(path):
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        mock_gauth.credentials = MagicMock()
        mock_gauth.access_token_expired = False

        # Inject mock into existing manager
        self.manager.gauth = mock_gauth

        mock_drive_instance = MockDrive.return_value
        mock_file = MagicMock()

        # Mock ListFile empty
        mock_list = MagicMock()
        mock_list.GetList.return_value = []
        mock_drive_instance.ListFile.return_value = mock_list

        mock_drive_instance.CreateFile.return_value = mock_file

        self.manager.upload_file("test.txt", provider="google_drive")

        mock_gauth.Authorize.assert_called()
        # Checks ListFile first
        mock_drive_instance.CreateFile.assert_called_with({"title": "test.txt"})
        mock_file.SetContentFile.assert_called_with("test.txt")
        mock_file.Upload.assert_called()

    @patch("os.path.exists")
    @patch("pydrive2.auth.GoogleAuth")
    @patch("pydrive2.drive.GoogleDrive")
    def test_upload_google_drive_refresh_token(self, MockDrive, MockAuth, mock_exists):
        def side_effect(path):
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        mock_gauth.credentials = MagicMock()
        mock_gauth.access_token_expired = True

        self.manager.gauth = mock_gauth

        self.manager.upload_file("test.txt")

        mock_gauth.Refresh.assert_called()

    @patch("os.path.exists")
    @patch("pydrive2.auth.GoogleAuth")
    def test_upload_google_drive_no_creds_headless(self, MockAuth, mock_exists):
        def side_effect(path):
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        mock_gauth.credentials = None

        self.manager.gauth = mock_gauth

        with patch.dict(os.environ, {"HEADLESS_MODE": "1"}):
            with self.assertRaisesRegex(
                Exception, "Cannot authenticate in headless mode"
            ):
                self.manager.upload_file("test.txt")

    @patch("os.path.exists")
    @patch("pydrive2.auth.GoogleAuth")
    @patch("pydrive2.drive.GoogleDrive")
    def test_upload_google_drive_no_creds_interactive(
        self, MockDrive, MockAuth, mock_exists
    ):
        def side_effect(path):
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        mock_gauth.credentials = None

        self.manager.gauth = mock_gauth

        # Ensure not headless and not CI to allow interactive auth
        with patch.dict(os.environ):
            if "HEADLESS_MODE" in os.environ:
                del os.environ["HEADLESS_MODE"]
            if "CI" in os.environ:
                del os.environ["CI"]

            self.manager.upload_file("test.txt")

        mock_gauth.LocalWebserverAuth.assert_called()

    @patch("os.path.exists")
    def test_upload_google_drive_import_error(self, mock_exists):
        def side_effect(path):
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        # clear cached gauth to force re-initialization logic
        self.manager.gauth = None

        # Simulate import error from pydrive2
        with patch("pydrive2.auth.GoogleAuth", side_effect=ImportError):
            with self.assertRaisesRegex(Exception, "PyDrive2 dependency missing"):
                self.manager.upload_file("test.txt")

    @patch("os.path.exists")
    @patch("pydrive2.auth.GoogleAuth")
    def test_upload_google_drive_general_exception(self, MockAuth, mock_exists):
        def side_effect(path):
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        mock_gauth.credentials = MagicMock()
        mock_gauth.access_token_expired = False
        mock_gauth.Authorize.side_effect = Exception("Auth failed")

        self.manager.gauth = mock_gauth

        with self.assertRaisesRegex(Exception, "Auth failed"):
            self.manager.upload_file("test.txt")
