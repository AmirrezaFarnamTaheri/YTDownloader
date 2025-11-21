import unittest
from unittest.mock import MagicMock, patch, ANY, mock_open
import sys
import os
import time
from datetime import datetime
import threading

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import flet as ft
# Mock flet before importing main because main imports flet and some controls might need it
# Actually we can let it import, but we need to mock controls in tests

from queue_manager import QueueManager
from history_manager import HistoryManager
from config_manager import ConfigManager

# Create a dummy main for testing logic if needed, or just test components
# Since main.py is now refactored, we should test QueueManager separately and logic in isolation if possible.

class TestQueueManager(unittest.TestCase):
    def setUp(self):
        self.qm = QueueManager()

    def test_add_remove_item(self):
        item = {'url': 'http://test', 'status': 'Queued'}
        self.qm.add_item(item)
        self.assertEqual(len(self.qm.get_all()), 1)

        self.qm.remove_item(item)
        self.assertEqual(len(self.qm.get_all()), 0)

    def test_swap_items(self):
        item1 = {'url': '1', 'status': 'Queued'}
        item2 = {'url': '2', 'status': 'Queued'}
        self.qm.add_item(item1)
        self.qm.add_item(item2)

        self.qm.swap_items(0, 1)
        items = self.qm.get_all()
        self.assertEqual(items[0], item2)
        self.assertEqual(items[1], item1)

    def test_find_next_downloadable(self):
        item1 = {'url': '1', 'status': 'Completed'}
        item2 = {'url': '2', 'status': 'Queued'}
        self.qm.add_item(item1)
        self.qm.add_item(item2)

        next_item = self.qm.find_next_downloadable()
        self.assertEqual(next_item, item2)

    def test_threading_lock(self):
        # Basic race condition check
        threads = []
        for i in range(100):
            t = threading.Thread(target=self.qm.add_item, args=({'id': i, 'status': 'Queued'},))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(self.qm.get_all()), 100)


class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        # Use in-memory DB for testing if possible, but HistoryManager uses a fixed path.
        # We will mock the DB connection.
        pass

    @patch('history_manager.sqlite3.connect')
    def test_add_entry(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        HistoryManager.add_entry("http://test", "Test", "/tmp", "mp4", "Completed", "10MB")

        mock_cursor.execute.assert_called()
        self.assertIn("INSERT INTO history", mock_cursor.execute.call_args[0][0])


class TestConfigManager(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": 1}')
    @patch("config_manager.Path.exists", return_value=True)
    def test_load_config(self, mock_exists, mock_file):
        # We need to mock Path.exists from config_manager, not os.path.exists
        # Also, read_data should be sufficient for json.load if using built-in open
        config = ConfigManager.load_config()
        self.assertEqual(config.get("test"), 1)

    @patch("builtins.open", new_callable=mock_open)
    def test_save_config(self, mock_file):
        ConfigManager.save_config({"test": 2})
        mock_file.assert_called_with(ANY, 'w', encoding='utf-8')

if __name__ == '__main__':
    unittest.main()
