import sqlite3
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

from history_manager import HistoryManager


class TestHistoryManagerRobustness(unittest.TestCase):

    def setUp(self):
        self.db_patcher = patch(
            "history_manager.HistoryManager.DB_FILE",
            Path("test_history_robust.db"),
            create=True,
        )
        self.mock_db_file = self.db_patcher.start()
        # We also need to patch the module level DB_FILE if it's used directly
        self.module_db_patcher = patch(
            "history_manager.DB_FILE", Path("test_history_robust.db")
        )
        self.module_db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()
        self.module_db_patcher.stop()
        if Path("test_history_robust.db").exists():
            try:
                Path("test_history_robust.db").unlink()
            except:
                pass

    @patch("history_manager.sqlite3.connect")
    def test_db_locked_retry(self, mock_connect):
        # Mock connect to raise OperationalError "locked" twice, then succeed
        mock_conn = MagicMock()
        mock_connect.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is locked"),
            mock_conn,
        ]

        # We need to mock _get_connection internals basically?
        # Actually _get_connection calls sqlite3.connect.
        # But `init_db` calls `_get_connection`.

        # Testing init_db retries
        with patch("time.sleep") as mock_sleep:  # Speed up tests
            HistoryManager.init_db()

        self.assertEqual(mock_connect.call_count, 3)

    @patch("history_manager.sqlite3.connect")
    def test_db_locked_failure(self, mock_connect):
        # Always locked
        mock_connect.side_effect = sqlite3.OperationalError("database is locked")

        with patch("time.sleep"):
            with self.assertRaises(sqlite3.OperationalError):
                HistoryManager.init_db()

        # Should try MAX_DB_RETRIES (3)
        self.assertEqual(mock_connect.call_count, 3)

    def test_validate_input_errors(self):
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("", "title", "path")

        with self.assertRaises(ValueError):
            HistoryManager._validate_input("ftp://bad", "title", "A" * 1025)

        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://good", "Bad DROP TABLE", "path")

    @patch("history_manager.sqlite3.connect")
    def test_add_entry_locked_retry(self, mock_connect):
        mock_conn = MagicMock()
        # Mocking context manager behavior of connection
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None

        # Mock connect success, but execute failure?
        # _get_connection returns a wrapper around conn.
        # So first call to connect succeeds.
        # Then inside `add_entry` -> `_get_connection`.

        # If we want to simulate lock during `_get_connection`, we mock `connect`.
        # If we want to simulate lock during `execute`, we mock cursor.

        # Let's mock `connect` raising locked.
        mock_connect.side_effect = [
            sqlite3.OperationalError("database is locked"),
            mock_conn,
        ]

        with patch("time.sleep"):
            HistoryManager.add_entry("http://u", "t", "p", "f", "s", "sz")

        self.assertEqual(mock_connect.call_count, 2)
