import pytest
import sqlite3
from unittest.mock import MagicMock, patch
from history_manager import HistoryManager

class TestHistoryManagerExtra:

    def test_validate_input_errors(self):
        # URL empty
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            HistoryManager._validate_input("", "title", "path")

        # URL too long
        with pytest.raises(ValueError, match="URL too long"):
            HistoryManager._validate_input("a" * 2049, "title", "path")

        # Title too long
        with pytest.raises(ValueError, match="Title too long"):
            HistoryManager._validate_input("url", "a" * 501, "path")

        # Output path too long
        with pytest.raises(ValueError, match="Output path too long"):
            HistoryManager._validate_input("url", "title", "a" * 1025)

        # Null bytes
        with pytest.raises(ValueError, match="Null bytes not allowed"):
            HistoryManager._validate_input("url\x00", "title", "path")

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_retry_success(self, mock_conn):
        # Simulate locked error then success

        # Setup mock_conn to return a mock object that has __enter__
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_db

        # We want the execute call to fail the first time
        # The code: with _get_connection() as conn: cursor = conn.cursor(); cursor.execute(...)

        # 1. First attempt: Raises Locked
        # 2. Retry loop sleeps.
        # 3. Second attempt: Success (Create Table)
        # 4. Pragma table_info
        # 5. Fetchall (handled by fetchall return value)
        # 6. Alter Table (because we will make fetchall return empty or missing column)
        # 7. Index 1
        # 8. Index 2
        # 9. Index 3

        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError("database is locked"), # 1
            None, # 3 (Create Table)
            None, # 4 (Pragma)
            None, # 6 (Alter Table)
            None, # 7 (Index 1)
            None, # 8 (Index 2)
            None  # 9 (Index 3)
        ]

        # The fetchall call returns empty columns so 'file_path' is missing
        mock_cursor.fetchall.return_value = []

        HistoryManager.init_db()

        assert mock_cursor.execute.call_count >= 6

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_retry_fail(self, mock_conn):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_db

        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")

        # Reduce retry count for speed
        with patch("history_manager.HistoryManager.MAX_DB_RETRIES", 2), \
             patch("time.sleep"):
            with pytest.raises(sqlite3.OperationalError, match="database is locked"):
                HistoryManager.init_db()

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_locked_retry_fail(self, mock_conn):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_db

        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")

        with patch("history_manager.HistoryManager.MAX_DB_RETRIES", 2), \
             patch("time.sleep"):
            with pytest.raises(sqlite3.OperationalError, match="database is locked"):
                HistoryManager.add_entry("url", "title", "path", "mp4", "Done", "10MB")
