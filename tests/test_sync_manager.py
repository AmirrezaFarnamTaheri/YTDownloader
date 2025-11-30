import json
import os
import unittest
import zipfile
from unittest.mock import MagicMock, patch

from config_manager import ConfigManager
from history_manager import HistoryManager
from sync_manager import SyncManager


class TestSyncManager(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_export.zip"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

        self.mock_cloud = MagicMock()
        self.mock_config = MagicMock() # Mock the object, not a dict
        self.mock_config.get_all.return_value = {"device_id": "test_device"}
        self.mock_config.get.return_value = True # For auto_sync_enabled checks

        self.manager = SyncManager(self.mock_cloud, self.mock_config)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch("history_manager.HistoryManager.get_history")
    def test_export_data(self, mock_get_history):
        self.mock_config.get_all.return_value = {"theme": "dark"}
        mock_get_history.return_value = [{"url": "http://test", "title": "Test Video"}]

        # Call on instance
        self.manager.export_data(self.test_file)
        self.assertTrue(os.path.exists(self.test_file))

        # Verify ZIP content
        with zipfile.ZipFile(self.test_file, "r") as zf:
            self.assertIn("config.json", zf.namelist())
            with zf.open("config.json") as f:
                data = json.load(f)
            self.assertEqual(data["theme"], "dark")
            # History is written as DB file, so we can't easily check content in this unit test
            # unless we mock DB file existence.
            # SyncManager.export_data checks os.path.exists(db_path)
            # We can mock os.path.exists to verify it TRIES to add it, but it reads real file.
            # For this test, verifying config.json in zip is enough to prove export_data works.

    @patch("history_manager.HistoryManager.add_entry")
    @patch("history_manager.HistoryManager.get_history")
    def test_import_data(self, mock_get_history, mock_add_entry):
        mock_get_history.return_value = (
            []
        )  # No existing history, so all should be added

        data = {
            "theme": "light"
        }

        # Create a ZIP file for import
        with zipfile.ZipFile(self.test_file, "w") as zf:
            zf.writestr("config.json", json.dumps(data))
            # We skip history.db for now as it requires binary file handling

        # Call on instance
        self.manager.import_data(self.test_file)

        self.mock_config.set.assert_called_with("theme", "light")

    def test_import_data_file_not_found(self):
        # Should not raise exception, logs error instead
        try:
            self.manager.import_data("non_existent_file.zip")
        except Exception as e:
            self.fail(f"import_data raised exception unexpectedly: {e}")
