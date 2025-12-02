"""
Unit tests for HistoryManager.
"""

import unittest
from unittest.mock import MagicMock, patch

from history_manager import HistoryManager


class TestHistoryManager(unittest.TestCase):

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # _get_connection returns connection object directly (not context manager)
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        HistoryManager.add_entry(
            "http://test", "Test", "/tmp", "mp4", "Completed", "10MB"
        )

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    @patch("history_manager.HistoryManager._get_connection")
    def test_get_history(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchone for COUNT
        mock_cursor.fetchone.return_value = [5] # Total count

        # Mock fetchall for SELECT
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
        self.assertEqual(history[0]["url"], "http://test")
