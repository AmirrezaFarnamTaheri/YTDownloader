# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import json
import os
import unittest
import zipfile
from unittest.mock import MagicMock, patch

from sync_manager import SyncManager


class TestSyncManager(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_export.zip"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

        self.mock_cloud = MagicMock()
        self.mock_config = MagicMock()  # Mock the object, not a dict
        self.mock_config.get_all.return_value = {"device_id": "test_device"}
        self.mock_config.get.return_value = True  # For auto_sync_enabled checks
        # Mocking hasattr(self.config, "load_config") is tricky on a MagicMock
        # SyncManager logic: if hasattr(config, load_config) -> call load_config
        # else if hasattr(config, get_all) -> call get_all
        # MagicMock has everything by default.
        # But for set vs save_config, we need to be careful.

        self.manager = SyncManager(self.mock_cloud, self.mock_config)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch("history_manager.HistoryManager.get_history")
    def test_export_data(self, mock_get_history):
        self.mock_config.get_all.return_value = {"theme": "dark"}
        # Ensure load_config is not favored if we want to test get_all path,
        # OR just mock load_config.
        self.mock_config.load_config.side_effect = AttributeError("No load_config")
        # Actually, let's just make load_config return the data, as that's the preferred path
        self.mock_config.load_config = MagicMock(return_value={"theme": "dark"})

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

    @patch("history_manager.HistoryManager.add_entry")
    @patch("history_manager.HistoryManager.get_history")
    def test_import_data(self, mock_get_history, mock_add_entry):
        mock_get_history.return_value = []

        data = {"theme": "light"}

        # Create a ZIP file for import
        with zipfile.ZipFile(self.test_file, "w") as zf:
            zf.writestr("config.json", json.dumps(data))

        # We need to decide if config has save_config or set.
        # Let's mock save_config to fail attribute check, so it falls back to set?
        # Or just mock set.
        # MagicMock has both. SyncManager checks save_config first.

        # Scenario 1: Config has save_config
        self.mock_config.save_config = MagicMock()
        self.manager.import_data(self.test_file)
        self.mock_config.save_config.assert_called_with(data)

        # Scenario 2: Config has only set (legacy/mock)
        # We need a new manager or config for this
        del self.mock_config.save_config

        # Reset
        self.manager.import_data(self.test_file)
        # In the loop: for k,v in data.items(): config.set(k, v)
        self.mock_config.set.assert_any_call("theme", "light")

    def test_import_data_file_not_found(self):
        # Should raise exception now as we removed the swallowing in SyncManager
        # per the "fix bugs" requirement (silencing errors is bad for debugging)
        # However, if the original test required silencing, we changed behavior.
        # Let's assert it RAISES now.
        with self.assertRaises(FileNotFoundError):
            self.manager.import_data("non_existent_file.zip")

    def test_resolve_history_db_path_fallback_for_invalid_mock_path(self):
        history = MagicMock()
        history._resolve_db_file.return_value = MagicMock()
        manager = SyncManager(self.mock_cloud, self.mock_config, history)

        resolved = manager._resolve_history_db_path()

        self.assertEqual(resolved, os.path.expanduser("~/.streamcatch/history.db"))
