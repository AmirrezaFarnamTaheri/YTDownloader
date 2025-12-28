# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Tests for HistoryManager.
"""

import os
import sqlite3
import unittest
from pathlib import Path

from history_manager import HistoryManager


class TestHistoryManager(unittest.TestCase):

    def setUp(self):
        # Use a temporary DB file for testing
        self.db_file = Path("test_history.db")
        if self.db_file.exists():
            os.remove(self.db_file)

        # Patch the class-level DB_FILE via a property or by patching the module level
        # HistoryManager._resolve_db_file uses _test_db_file if present
        HistoryManager._test_db_file = self.db_file

    def tearDown(self):
        if self.db_file.exists():
            try:
                os.remove(self.db_file)
            except OSError:
                pass
        # Reset
        if hasattr(HistoryManager, "_test_db_file"):
            del HistoryManager._test_db_file

    def test_init_db(self):
        HistoryManager.init_db()
        self.assertTrue(self.db_file.exists())

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='history'"
        )
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_add_and_get_history(self):
        HistoryManager.init_db()

        # Ensure clean state
        HistoryManager.clear_history()

        HistoryManager.add_entry(
            "http://test",
            "Test Title",
            "/tmp",
            "mp4",
            "Completed",
            "10MB",
            "/tmp/file.mp4",
        )

        history = HistoryManager.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["url"], "http://test")
        self.assertEqual(history[0]["status"], "Completed")

    def test_clear_history(self):
        HistoryManager.init_db()
        HistoryManager.add_entry("http://t", "T", ".", "mp4", "Done", "1MB")

        HistoryManager.clear_history()
        self.assertEqual(len(HistoryManager.get_history()), 0)

    def test_add_entry_validation(self):
        with self.assertRaises(ValueError):
            HistoryManager.add_entry("", "Title", ".", "mp4", "Done", "1MB")
