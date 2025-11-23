import unittest
from unittest.mock import patch, MagicMock
import sqlite3
from history_manager import HistoryManager


class TestHistoryManagerExtra(unittest.TestCase):
    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_exhausted_retries(self, mock_get_conn):
        """Test init_db exhausting retries on locked database."""
        # Mock connection to raise locked error every time
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn

        # Raise OperationalError with "locked" message
        locked_error = sqlite3.OperationalError("database is locked")
        mock_cursor.execute.side_effect = locked_error
        mock_get_conn.return_value = mock_conn

        with patch("time.sleep"):  # Skip sleep
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.init_db()

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_exhausted_retries(self, mock_get_conn):
        """Test add_entry exhausting retries on locked database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn

        locked_error = sqlite3.OperationalError("database is locked")
        mock_cursor.execute.side_effect = locked_error
        mock_get_conn.return_value = mock_conn

        with patch("time.sleep"):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.add_entry(
                    "http://url", "Title", "/tmp", "mp4", "finished", "10MB"
                )

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_generic_exception(self, mock_get_conn):
        """Test init_db generic exception handling."""
        mock_get_conn.side_effect = Exception("Generic DB Error")

        with self.assertRaises(Exception):
            HistoryManager.init_db()

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_generic_exception(self, mock_get_conn):
        """Test add_entry generic exception handling."""
        mock_get_conn.side_effect = Exception("Generic DB Error")

        with self.assertRaises(Exception):
            HistoryManager.add_entry(
                "http://url", "Title", "/tmp", "mp4", "finished", "10MB"
            )


if __name__ == "__main__":
    unittest.main()
