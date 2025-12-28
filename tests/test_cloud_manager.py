# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import os
import unittest
from unittest.mock import MagicMock, patch

from cloud_manager import CloudManager

# Check if PyDrive2 is available for tests that require it
try:
    import pydrive2  # noqa: F401 - import for availability check

    PYDRIVE2_AVAILABLE = True
except ImportError:
    PYDRIVE2_AVAILABLE = False


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

    @unittest.skipUnless(PYDRIVE2_AVAILABLE, "PyDrive2 not installed")
    @patch("os.path.exists")
    def test_upload_google_drive_missing_secrets(self, mock_exists):
        # File exists, but client_secrets.json does not
        def side_effect(path):
            if path == "test.txt":
                return True
            if "client_secrets.json" in str(path):
                return False
            return False

        mock_exists.side_effect = side_effect

        with self.assertRaisesRegex(Exception, "Google Drive not configured"):
            self.manager.upload_file("test.txt", provider="google_drive")

    @unittest.skipUnless(PYDRIVE2_AVAILABLE, "PyDrive2 not installed")
    @patch("os.path.exists")
    @patch("cloud_manager._google_auth_cls")
    @patch("cloud_manager._google_drive_cls")
    def test_upload_google_drive_success(self, MockDrive, MockAuth, mock_exists):
        def side_effect(path):
            return (
                path == "test.txt"
                or "client_secrets.json" in str(path)
                or "mycreds.txt" in str(path)
            )

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        # Important: set credentials to truthy to avoid "None" check
        mock_gauth.credentials = MagicMock()
        # Important: set access_token_expired to False to avoid Refresh branch
        mock_gauth.access_token_expired = False

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

    @unittest.skipUnless(PYDRIVE2_AVAILABLE, "PyDrive2 not installed")
    @patch("os.path.exists")
    @patch("cloud_manager._google_auth_cls")
    @patch("cloud_manager._google_drive_cls")
    def test_upload_google_drive_refresh_token(self, MockDrive, MockAuth, mock_exists):
        def side_effect(path):
            return (
                path == "test.txt"
                or "client_secrets.json" in str(path)
                or "mycreds.txt" in str(path)
            )

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        mock_gauth.credentials = MagicMock()
        # Force expired token
        mock_gauth.access_token_expired = True

        self.manager.upload_file("test.txt")

        mock_gauth.Refresh.assert_called()

    @unittest.skipUnless(PYDRIVE2_AVAILABLE, "PyDrive2 not installed")
    @patch("os.path.exists")
    @patch("cloud_manager._google_auth_cls")
    def test_upload_google_drive_no_creds_headless(self, MockAuth, mock_exists):
        def side_effect(path):
            # NO credentials file
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        # Explicitly None to trigger auth flow
        mock_gauth.credentials = None

        with patch.dict(os.environ, {"HEADLESS_MODE": "1"}):
            with self.assertRaisesRegex(
                Exception, "Cannot authenticate in headless mode"
            ):
                self.manager.upload_file("test.txt")

    @unittest.skipUnless(PYDRIVE2_AVAILABLE, "PyDrive2 not installed")
    @patch("os.path.exists")
    @patch("cloud_manager._google_auth_cls")
    @patch("cloud_manager._google_drive_cls")
    def test_upload_google_drive_no_creds_interactive(
        self, MockDrive, MockAuth, mock_exists
    ):
        def side_effect(path):
            # No credentials file exists for this test case
            return path == "test.txt" or "client_secrets.json" in str(path)

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        # Explicitly None to trigger auth flow
        mock_gauth.credentials = None

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
            return (
                path == "test.txt"
                or "client_secrets.json" in str(path)
                or "mycreds.txt" in str(path)
            )

        mock_exists.side_effect = side_effect

        # Force _google_auth_cls to be None in cloud_manager
        with patch("cloud_manager._google_auth_cls", None):
            with patch("cloud_manager._google_drive_cls", None):
                with self.assertRaisesRegex(Exception, "PyDrive2 dependency missing"):
                    self.manager.upload_file("test.txt")

    @unittest.skipUnless(PYDRIVE2_AVAILABLE, "PyDrive2 not installed")
    @patch("os.path.exists")
    @patch("cloud_manager._google_auth_cls")
    def test_upload_google_drive_general_exception(self, MockAuth, mock_exists):
        def side_effect(path):
            return (
                path == "test.txt"
                or "client_secrets.json" in str(path)
                or "mycreds.txt" in str(path)
            )

        mock_exists.side_effect = side_effect

        mock_gauth = MockAuth.return_value
        mock_gauth.credentials = MagicMock()
        mock_gauth.access_token_expired = False
        mock_gauth.Authorize.side_effect = Exception("Auth failed")

        with self.assertRaisesRegex(Exception, "Auth failed"):
            self.manager.upload_file("test.txt")
