"""
Robustness tests for HistoryManager.
"""

import unittest
from unittest.mock import MagicMock, patch

from history_manager import HistoryManager


class TestHistoryManagerRobustness(unittest.TestCase):

    def test_validate_input_valid(self):
        # Should not raise
        HistoryManager._validate_input("http://url", "Title", "Path")

    def test_validate_input_errors(self):
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("", "title", "path")

        # Test length limit
        long_url = "a" * 2050
        with self.assertRaises(ValueError):
            HistoryManager._validate_input(long_url, "title", "path")

    def test_validate_input_null_bytes(self):
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://\x00", "title", "path")

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_indefinitely(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Simulate locked DB
        import sqlite3
        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")

        with patch("history_manager.HistoryManager.DB_RETRY_DELAY", 0.001):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.init_db()
