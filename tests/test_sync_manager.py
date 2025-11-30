import json
import os
import unittest
from unittest.mock import MagicMock, patch

from config_manager import ConfigManager
from history_manager import HistoryManager
from sync_manager import SyncManager


class TestSyncManager(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_export.json"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

        self.mock_cloud = MagicMock()
        self.mock_config = {"device_id": "test_device"}
        self.manager = SyncManager(self.mock_cloud, self.mock_config)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch("config_manager.ConfigManager.load_config")
    @patch("history_manager.HistoryManager.get_history")
    def test_export_data(self, mock_get_history, mock_load_config):
        mock_load_config.return_value = {"theme": "dark"}
        mock_get_history.return_value = [{"url": "http://test", "title": "Test Video"}]

        # Call on instance
        self.manager.export_data(self.test_file)
        self.assertTrue(os.path.exists(self.test_file))

        with open(self.test_file, "r") as f:
            data = json.load(f)

        self.assertEqual(data["config"]["theme"], "dark")
        self.assertEqual(data["history"][0]["title"], "Test Video")

    @patch("config_manager.ConfigManager.save_config")
    @patch("history_manager.HistoryManager.add_entry")
    @patch("history_manager.HistoryManager.get_history")
    def test_import_data(self, mock_get_history, mock_add_entry, mock_save_config):
        mock_get_history.return_value = [] # No existing history, so all should be added

        data = {
            "config": {"theme": "light"},
            "history": [
                {
                    "url": "http://test2",
                    "title": "Test Video 2",
                    "output_path": "/tmp",
                    "format_str": "mp4",
                    "status": "Completed",
                    "file_size": "10MB",
                }
            ],
        }
        with open(self.test_file, "w") as f:
            json.dump(data, f)

        # Call on instance
        self.manager.import_data(self.test_file)

        mock_save_config.assert_called_with({"theme": "light"})

        # Verify add_entry is called
        mock_add_entry.assert_called_once()
        args, kwargs = mock_add_entry.call_args
        self.assertEqual(kwargs.get("url"), "http://test2")
        self.assertEqual(kwargs.get("title"), "Test Video 2")

    def test_import_data_file_not_found(self):
        # Should not raise exception, logs error instead
        try:
            self.manager.import_data("non_existent_file.json")
        except Exception as e:
            self.fail(f"import_data raised exception unexpectedly: {e}")
