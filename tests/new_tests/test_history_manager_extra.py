"""
Extra coverage tests for HistoryManager.
"""

import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from history_manager import HistoryManager


class TestHistoryManagerExtra(unittest.TestCase):
    """Test suite for HistoryManager extra coverage."""

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_generic_exception(self, mock_get_conn):
        """Test init_db generic exception handling."""
        mock_get_conn.side_effect = Exception("Generic DB Error")

        # The updated code re-raises exceptions to prevent silent failures
        # So we expect it to raise
        with self.assertRaises(Exception):
            HistoryManager.init_db()

    @patch("history_manager.HistoryManager._get_connection")
    def test_get_history_paginated_empty(self, mock_get_conn):
        """Test get_history_paginated with no results."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = [0]
        mock_cursor.fetchall.return_value = []

        result = HistoryManager.get_history_paginated()
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["entries"], [])
        self.assertFalse(result["has_more"])

    @patch("history_manager.HistoryManager._get_connection")
    def test_get_history_paginated_error(self, mock_get_conn):
        """Test get_history_paginated error handling."""
        mock_get_conn.side_effect = Exception("DB Error")

        result = HistoryManager.get_history_paginated()
        # Should handle gracefully and return empty structure
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["total"], 0)

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_max_retries_exceeded(self, mock_get_conn):
        """Test that exception is raised after max retries."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Always locked
        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")

        with patch("history_manager.HistoryManager.DB_RETRY_DELAY", 0.001):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.add_entry(
                    "url", "title", "path", "fmt", "status", "size"
                )

        self.assertEqual(mock_cursor.execute.call_count, 3)
