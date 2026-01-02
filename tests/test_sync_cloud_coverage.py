# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for SyncManager and CloudManager.
"""

import os
import unittest
import zipfile
from unittest.mock import MagicMock, patch

from cloud_manager import CloudManager
from sync_manager import SyncManager

# Check if PyDrive2 is available for tests that require it
try:
    import pydrive2  # noqa: F401 - import for availability check

    PYDRIVE2_AVAILABLE = True
except ImportError:
    PYDRIVE2_AVAILABLE = False


class TestSyncManagerCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_cloud = MagicMock(spec=CloudManager)
        self.mock_config = MagicMock()
        self.mock_history = MagicMock()
        self.manager = SyncManager(self.mock_cloud, self.mock_config, self.mock_history)

    def test_init(self):
        """Test SyncManager initialization stores dependencies correctly."""
        self.assertIsNotNone(self.manager)
        # SyncManager stores cloud as 'cloud' and config as 'config'
        self.assertEqual(self.manager.cloud, self.mock_cloud)
        self.assertEqual(self.manager.config, self.mock_config)

    @patch("zipfile.ZipFile")
    @patch("os.path.exists")
    def test_export_data(self, mock_exists, mock_zip):
        mock_exists.return_value = True  # for history.db

        # Mock Config return
        # Mock load_config which is called by _get_config_snapshot
        self.mock_config.load_config.return_value = {"theme": "dark"}

        # Call with required path
        self.manager.export_data("backup.zip")

        # Verify zip interactions
        mock_zip.assert_called_with("backup.zip", "w", zipfile.ZIP_DEFLATED)
        mock_zip.return_value.__enter__.return_value.writestr.assert_called()  # config
        mock_zip.return_value.__enter__.return_value.write.assert_called()  # history

    def test_export_data_failure(self):
        # Trigger exception
        # export_data re-raises the exception
        # sync_manager calls load_config if available, then get_all.
        self.mock_config.load_config.side_effect = RuntimeError("Config Error")

        with self.assertRaises(RuntimeError):
            self.manager.export_data("backup.zip")

    @patch("shutil.copyfileobj")
    @patch("builtins.open")
    @patch("zipfile.ZipFile")
    @patch("os.path.exists")
    def test_import_data(self, mock_exists, mock_zip, mock_open, mock_copyfileobj):
        mock_exists.return_value = True

        # Mock zip content
        mock_zf = mock_zip.return_value.__enter__.return_value

        # New SyncManager iterates infolist(), not namelist()
        config_entry = MagicMock()
        config_entry.filename = "config.json"

        history_entry = MagicMock()
        history_entry.filename = "history.db"

        mock_zf.infolist.return_value = [config_entry, history_entry]
        # namelist also used by _import_history_db check
        mock_zf.namelist.return_value = ["config.json", "history.db"]

        # Mock opening file from zip for config.json AND history.db
        mock_read_file = MagicMock()
        # For config.json, json.load calls read(). For copyfileobj, it reads bytes.
        mock_read_file.read.return_value = b'{"theme": "light"}'

        # When opening config.json or history.db, return this file mock
        mock_zf.open.return_value.__enter__.return_value = mock_read_file

        self.manager.import_data("backup.zip")

        # Verify restoration
        self.mock_config.save_config.assert_called_with({"theme": "light"})
        # Verify copyfileobj was called
        mock_copyfileobj.assert_called()

    def test_import_data_no_backups(self):
        # This test case from previous run was for Cloud backup listing,
        # but import_data takes a file path.
        # If file doesn't exist:
        with patch("os.path.exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                self.manager.import_data("missing.zip")


class TestCloudManagerCoverage(unittest.TestCase):
    def setUp(self):
        self.manager = CloudManager()
        self.manager.gauth = MagicMock()
        self.manager.drive = MagicMock()

    @unittest.skipUnless(PYDRIVE2_AVAILABLE, "PyDrive2 not installed")
    @patch("cloud_manager.os.path.exists")
    def test_get_google_drive_client_no_creds(self, mock_exists):
        # Mock existence: client_secrets.json -> False
        mock_exists.return_value = False

        # We need to force a condition where it raises or returns None
        # With CI environment variable set in test environment, it returns None
        # We can patch os.environ to ensure specific behavior if needed
        # Or assert behavior based on current env
        # The original test expected an exception "not configured".
        # But implementation might have changed to return None in CI.

        # Let's inspect implementation:
        # if not client_secrets and not mycreds: return None (if CI) or raise.

        # We patch os.environ to ensure consistent test behavior (NOT CI)
        with patch.dict(os.environ, {}, clear=True):
            # Ensure CI is NOT set
            with self.assertRaises(Exception) as cm:
                self.manager._get_google_drive_client()
            self.assertIn("not configured", str(cm.exception))

    @patch("cloud_manager._google_auth_cls")
    @patch("cloud_manager._google_drive_cls")
    @patch("cloud_manager.os.path.exists")
    def test_get_google_drive_client_success(self, mock_exists, mock_drive, mock_gauth):
        # Clean environment to prevent CI/Headless logic from triggering
        with patch.dict(os.environ, {}, clear=True):
            # Mock existence: client_secrets.json -> True, mycreds.txt -> False
            def exists_side_effect(path):
                if "client_secrets.json" in str(path):
                    return True
                if "mycreds.txt" in str(path):
                    return False
                return False

            mock_exists.side_effect = exists_side_effect

            # Mock Auth flow
            auth_instance = mock_gauth.return_value
            # Ensure credentials are None to trigger authentication
            auth_instance.credentials = None
            # Ensure access_token_expired is False to avoid that branch
            auth_instance.access_token_expired = False

            client = self.manager._get_google_drive_client()

            auth_instance.LocalWebserverAuth.assert_called()
            auth_instance.SaveCredentialsFile.assert_called()
            self.assertEqual(client, mock_drive.return_value)

    @patch("cloud_manager.os.path.exists")
    def test_upload_file_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            self.manager.upload_file("test.zip")

    @patch("cloud_manager.CloudManager._get_google_drive_client")
    @patch("cloud_manager.os.path.exists")
    def test_upload_file_success(self, mock_exists, mock_get_client):
        mock_exists.return_value = True
        mock_drive = mock_get_client.return_value
        mock_file = MagicMock()
        mock_drive.ListFile.return_value.GetList.return_value = []  # New file
        mock_drive.CreateFile.return_value = mock_file

        self.manager.upload_file("test.zip")

        mock_file.SetContentFile.assert_called_with("test.zip")
        mock_file.Upload.assert_called()

    @patch("cloud_manager.CloudManager._get_google_drive_client")
    def test_download_file_success(self, mock_get_client):
        mock_drive = mock_get_client.return_value
        mock_file = MagicMock()
        mock_file.__getitem__.return_value = "file_id"
        mock_drive.ListFile.return_value.GetList.return_value = [mock_file]

        res = self.manager.download_file("backup.zip", "dest.zip")

        self.assertTrue(res)
        mock_file.GetContentFile.assert_called_with("dest.zip")

    def test_upload_file_unsupported_provider(self):
        with patch("cloud_manager.os.path.exists", return_value=True):
            with self.assertRaises(NotImplementedError):
                self.manager.upload_file("test.zip", provider="unknown")
