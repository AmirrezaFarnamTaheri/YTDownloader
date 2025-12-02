import sqlite3
import unittest
from unittest.mock import ANY, MagicMock, patch

from history_manager import DB_FILE, HistoryManager


class TestHistoryManagerCoverage(unittest.TestCase):

    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_retry(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn

        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            None,
            None,
            None,
            None,
            None,
        ]

        mock_cursor.fetchall.return_value = [(0, "file_path")]

        with patch("history_manager.HistoryManager.DB_RETRY_DELAY", 0.01):
            HistoryManager.init_db()

        self.assertGreaterEqual(mock_cursor.execute.call_count, 6)


    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_locked_failure(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.execute.side_effect = sqlite3.OperationalError("database is locked")

        with patch("history_manager.HistoryManager.DB_RETRY_DELAY", 0.001):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.init_db()


    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_other_error(self, mock_get_conn):
        mock_get_conn.side_effect = Exception("General failure")
        with self.assertRaises(Exception):
            HistoryManager.init_db()


    def test_validate_input_edge_cases(self):
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://url\x00", "Title", "path")
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://url", "Title\x00", "path")
        long_url = "http://" + "a" * 2050
        with self.assertRaises(ValueError):
            HistoryManager._validate_input(long_url, "Title", "path")


    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_locked_retry(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

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
        entries = HistoryManager.get_history()
        self.assertEqual(entries, [])


    @patch("sqlite3.connect")
    def test_clear_history_error(self, mock_connect):
        # We now use _get_connection which uses sqlite3.connect
        # Mocking _get_connection is safer if we want to bypass connection logic
        with patch("history_manager.HistoryManager._get_connection", side_effect=Exception("DB Down")):
             with self.assertRaises(Exception):
                 HistoryManager.clear_history()


    @patch("sqlite3.connect")
    @patch("pathlib.Path.mkdir")
    @patch("os.access")
    @patch("pathlib.Path.exists")
    def test_get_connection(self, mock_exists, mock_access, mock_mkdir, mock_connect):
        # If exists returns True, mkdir is NOT called
        mock_exists.return_value = True
        mock_access.return_value = True

        conn = HistoryManager._get_connection()
        mock_connect.assert_called()

        # Test case where it DOES not exist
        mock_exists.return_value = False
        # To test mkdir, we need .parent to return a path that triggers mkdir
        # DB_FILE.parent.exists() is called.

        conn = HistoryManager._get_connection()
        mock_mkdir.assert_called()


    @patch("history_manager.HistoryManager._get_connection")
    def test_init_db_migration(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "url", "TEXT", 1, None, 0),
        ]

        mock_cursor.execute.side_effect = None

        HistoryManager.init_db()

        found_alter = False
        for call in mock_cursor.execute.call_args_list:
            if "ALTER TABLE" in call[0][0]:
                found_alter = True
                break
        self.assertTrue(found_alter)


    @patch("history_manager.HistoryManager._get_connection")
    def test_add_entry_success(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        HistoryManager.add_entry(
            "http://url", "Title", "/path", "mp4", "Completed", "10MB"
        )
        mock_conn.commit.assert_called()


    @patch("history_manager.HistoryManager._get_connection")
    def test_get_history_success(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = [1]
        mock_cursor.fetchall.return_value = [
            {"id": 1, "url": "test"}
        ]

        entries = HistoryManager.get_history(limit=10)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["url"], "test")


    @patch("history_manager.HistoryManager._get_connection")
    def test_clear_history_success(self, mock_get_conn):
        # We patched HistoryManager to use _get_connection
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        HistoryManager.clear_history()

        # Now we check calls on the connection returned by _get_connection
        mock_conn.execute.assert_any_call("DELETE FROM history")
        mock_conn.execute.assert_any_call("VACUUM")
