import os
import sys
import unittest
from unittest.mock import ANY, MagicMock, mock_open, patch

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from history_manager import HistoryManager


class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        # We mock sqlite3 so no real DB is touched
        pass

    @patch("history_manager.sqlite3.connect")
    def test_add_entry(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        HistoryManager.add_entry(
            "http://test", "Test", "/tmp", "mp4", "Completed", "10MB"
        )

        mock_cursor.execute.assert_called()
        self.assertIn("INSERT INTO history", mock_cursor.execute.call_args[0][0])

    @patch("history_manager.sqlite3.connect")
    def test_get_history(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchall return - we return dicts because dict(dict) works, and it simulates sqlite3.Row conversion
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "url": "http://test",
                "title": "Test",
                "output_path": "/tmp",
                "format_str": "mp4",
                "status": "Completed",
                "timestamp": "2023-01-01",
                "file_size": "10MB",
                "file_path": "test.mp4",
            }
        ]

        history = HistoryManager.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["title"], "Test")


if __name__ == "__main__":
    unittest.main()
