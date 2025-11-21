import unittest
import json
import os
from unittest.mock import patch, MagicMock
from sync_manager import SyncManager
from config_manager import ConfigManager
from history_manager import HistoryManager


class TestSyncManager(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_export.json"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch("config_manager.ConfigManager.load_config")
    @patch("history_manager.HistoryManager.get_history")
    def test_export_data(self, mock_get_history, mock_load_config):
        mock_load_config.return_value = {"theme": "dark"}
        mock_get_history.return_value = [{"url": "http://test", "title": "Test Video"}]

        path = SyncManager.export_data(self.test_file)
        self.assertTrue(os.path.exists(path))

        with open(path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["config"]["theme"], "dark")
        self.assertEqual(data["history"][0]["title"], "Test Video")

    @patch("config_manager.ConfigManager.save_config")
    @patch("history_manager.HistoryManager.add_entry")
    def test_import_data(self, mock_add_entry, mock_save_config):
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

        SyncManager.import_data(self.test_file)

        mock_save_config.assert_called_with({"theme": "light"})
        mock_add_entry.assert_called_with(
            url="http://test2",
            title="Test Video 2",
            output_path="/tmp",
            format_str="mp4",
            status="Completed",
            file_size="10MB",
            file_path=None,
        )

    def test_import_data_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            SyncManager.import_data("non_existent_file.json")
