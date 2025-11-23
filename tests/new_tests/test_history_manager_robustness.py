import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import time
from history_manager import HistoryManager


class TestHistoryManagerRobustness(unittest.TestCase):
    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_exhausted(self, mock_get_conn):
        """Test init_db when database is locked and retries are exhausted."""
        # Create a mock connection context manager
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup mock to always raise OperationalError("database is locked")
        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")
        mock_get_conn.return_value = mock_conn

        # Mock time.sleep to speed up test
        with patch("time.sleep"):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.init_db()

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_generic_error(self, mock_get_conn):
        """Test init_db with a generic exception."""
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup mock to raise generic exception
        mock_cursor.execute.side_effect = Exception("Generic Error")
        mock_get_conn.return_value = mock_conn

        with self.assertRaises(Exception):
            HistoryManager.init_db()

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_locked_exhausted(self, mock_get_conn):
        """Test add_entry when database is locked and retries are exhausted."""
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")
        mock_get_conn.return_value = mock_conn

        with patch("time.sleep"):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.add_entry(
                    "http://url", "Title", "/tmp", "mp4", "finished", "10MB"
                )

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_generic_error(self, mock_get_conn):
        """Test add_entry with a generic exception."""
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.execute.side_effect = Exception("Generic Error")
        mock_get_conn.return_value = mock_conn

        with self.assertRaises(Exception):
            HistoryManager.add_entry(
                "http://url", "Title", "/tmp", "mp4", "finished", "10MB"
            )

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_operational_not_locked(self, mock_get_conn):
        """Test add_entry with OperationalError that is NOT locked."""
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.execute.side_effect = sqlite3.OperationalError("some other error")
        mock_get_conn.return_value = mock_conn

        with self.assertRaises(sqlite3.OperationalError):
            HistoryManager.add_entry(
                "http://url", "Title", "/tmp", "mp4", "finished", "10MB"
            )

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_operational_not_locked(self, mock_get_conn):
        """Test init_db with OperationalError that is NOT locked."""
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.execute.side_effect = sqlite3.OperationalError("some other error")
        mock_get_conn.return_value = mock_conn

        with self.assertRaises(sqlite3.OperationalError):
            HistoryManager.init_db()


if __name__ == "__main__":
    unittest.main()
