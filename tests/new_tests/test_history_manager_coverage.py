import sqlite3
import unittest
from unittest.mock import ANY, MagicMock, patch

from history_manager import DB_FILE, HistoryManager


class TestHistoryManagerCoverage(unittest.TestCase):

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_retry(self, mock_get_conn):
        # Simulate locked database that eventually succeeds
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn

        # Raise OperationalError("locked") twice, then succeed
        # Note: cursor.fetchall() consumes one item from side_effect if it's on cursor object?
        # No, fetchall is separate method. execute side_effect is for execute calls.

        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            None,  # CREATE TABLE
            None,  # PRAGMA table_info - wait, PRAGMA is an execute call!
            None,  # ALTER TABLE (if file_path missing) OR just next calls
            None,  # CREATE INDEX 1
            None,  # CREATE INDEX 2
            None,  # CREATE INDEX 3
        ]

        # We need to handle fetchall returning something that says file_path is missing to trigger ALTER TABLE
        # Or say it IS there to skip it.
        # Let's say it IS there to simplify
        mock_cursor.fetchall.return_value = [(0, "file_path")]

        # Adjusted side effect for the "file_path exists" path:
        # 1. Error
        # 2. Error
        # 3. CREATE TABLE
        # 4. PRAGMA table_info
        # 5. CREATE INDEX 1
        # 6. CREATE INDEX 2
        # 7. CREATE INDEX 3

        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            None,  # CREATE TABLE
            None,  # PRAGMA
            None,  # CREATE INDEX 1
            None,  # CREATE INDEX 2
            None,  # CREATE INDEX 3
        ]

        # Configure the successful connection
        mock_get_conn.return_value = mock_conn

        # Reduce retry delay for test
        with patch("history_manager.HistoryManager.DB_RETRY_DELAY", 0.01):
            HistoryManager.init_db()

        self.assertEqual(mock_cursor.execute.call_count, 7)

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_failure(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn

        # Always locked
        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")
        mock_get_conn.return_value = mock_conn

        with patch("history_manager.HistoryManager.DB_RETRY_DELAY", 0.001):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.init_db()

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_other_error(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("General failure")
        mock_conn.__enter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn

        # Now we expect it NOT to raise, but just log error
        HistoryManager.init_db()
        # Verify it handled it gracefully

    def test_validate_input_edge_cases(self):
        # Null bytes
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://url\x00", "Title", "path")
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://url", "Title\x00", "path")

        # Too long
        long_url = "http://" + "a" * 2050
        with self.assertRaises(ValueError):
            HistoryManager._validate_input(long_url, "Title", "path")

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_locked_retry(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn

        # Fail twice, then succeed
        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            None,
        ]

        with patch("history_manager.HistoryManager.DB_RETRY_DELAY", 0.01):
            HistoryManager.add_entry(
                "http://url", "title", "path", "fmt", "done", "10MB"
            )

        self.assertEqual(mock_cursor.execute.call_count, 3)

    @patch("history_manager.HistoryManager._get_connection")
    def test_get_history_error(self, mock_get_conn):
        mock_get_conn.side_effect = Exception("DB Down")
        # Should return empty list, not crash
        entries = HistoryManager.get_history()
        self.assertEqual(entries, [])

    @patch("history_manager.HistoryManager._get_connection")
    def test_clear_history_error(self, mock_get_conn):
        mock_get_conn.side_effect = Exception("DB Down")
        # Should log error and not crash
        HistoryManager.clear_history()

    @patch("sqlite3.connect")
    @patch("pathlib.Path.mkdir")
    @patch("os.access")
    @patch("pathlib.Path.exists")
    def test_get_connection(self, mock_exists, mock_access, mock_mkdir, mock_connect):
        mock_exists.return_value = True
        mock_access.return_value = True

        conn = HistoryManager._get_connection()
        mock_mkdir.assert_called()
        mock_connect.assert_called_with(DB_FILE, timeout=5.0)

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_migration(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn

        # Mock fetchall to return columns WITHOUT file_path to trigger migration
        # Columns returned by PRAGMA table_info are: (cid, name, type, notnull, dflt_value, pk)
        mock_cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "url", "TEXT", 1, None, 0),
        ]

        HistoryManager.init_db()

        # Check if ALTER TABLE was called
        found_alter = False
        for call in mock_cursor.execute.call_args_list:
            if "ALTER TABLE" in call[0][0]:
                found_alter = True
                break
        self.assertTrue(found_alter)

    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_success(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        HistoryManager.add_entry(
            "http://url", "Title", "/path", "mp4", "Completed", "10MB"
        )
        mock_conn.commit.assert_called()

    @patch("history_manager.HistoryManager._get_connection")
    def test_get_history_success(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Ensure _get_connection returns mock_conn
        mock_get_conn.return_value = mock_conn
        # Ensure context manager returns mock_conn
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Row factory simulation
        mock_cursor.fetchall.return_value = [
            {"id": 1, "url": "test"}  # Mocking dict-like rows
        ]

        entries = HistoryManager.get_history(limit=10)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["url"], "test")

    @patch("history_manager.HistoryManager._get_connection")
    def test_clear_history_success(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Ensure _get_connection returns mock_conn
        mock_get_conn.return_value = mock_conn
        # Ensure context manager returns mock_conn
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        HistoryManager.clear_history()
        # Check that DELETE was called (any call)
        mock_cursor.execute.assert_any_call("DELETE FROM history")
        mock_conn.commit.assert_called()
