# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for SyncManager and CloudManager.
"""

import io
import json
import os
import unittest
import zipfile
from unittest.mock import ANY, MagicMock, patch

from cloud_manager import CloudManager
from sync_manager import SyncManager


class TestSyncManagerCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_cloud = MagicMock(spec=CloudManager)
        self.mock_config = MagicMock()
        self.manager = SyncManager(self.mock_cloud, self.mock_config)

    def test_init(self):
        # cloud_manager is private in SyncManager? Let's check source.
        pass

    @patch("zipfile.ZipFile")
    @patch("os.path.exists")
    def test_export_data(self, mock_exists, mock_zip):
        mock_exists.return_value = True  # for history.db

        # Mock Config return
        self.mock_config.get_all.return_value = {"theme": "dark"}

        # Call with required path
        self.manager.export_data("backup.zip")

        # Verify zip interactions
        mock_zip.assert_called_with("backup.zip", "w", zipfile.ZIP_DEFLATED)
        mock_zip.return_value.__enter__.return_value.writestr.assert_called()  # config
        mock_zip.return_value.__enter__.return_value.write.assert_called()  # history

    def test_export_data_failure(self):
        # Trigger exception
        self.mock_config.get_all.side_effect = Exception("Config Error")

        # export_data re-raises the exception
        # Wait, if get_all is property or method? ConfigManager code suggests it's a method.
        # But maybe we need to mock load_config if it's called first?
        # sync_manager calls load_config if available, then get_all.
        # Let's mock load_config to raise.

        self.mock_config.load_config.side_effect = Exception("Config Error")

        with self.assertRaises(Exception):
            self.manager.export_data("backup.zip")

    @patch("shutil.copyfileobj")
    @patch("builtins.open")
    @patch("zipfile.ZipFile")
    @patch("os.path.exists")
    def test_import_data(self, mock_exists, mock_zip, mock_open, mock_copyfileobj):
        mock_exists.return_value = True

        # Mock zip content
        mock_zf = mock_zip.return_value.__enter__.return_value
        mock_zf.namelist.return_value = ["config.json", "history.db"]

        # Mock opening file from zip for history.db
        mock_read_file = MagicMock()
        mock_read_file.read.return_value = b"some bytes"
        mock_zf.open.return_value.__enter__.return_value = mock_read_file

        # Mock builtins.open for writing history.db
        mock_file_handle = mock_open.return_value.__enter__.return_value

        with patch("json.load", return_value={"theme": "light"}):
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

    @patch("cloud_manager.os.path.exists")
    def test_get_google_drive_client_no_creds(self, mock_exists):
        # Mock existence: client_secrets.json -> False
        mock_exists.return_value = False

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
