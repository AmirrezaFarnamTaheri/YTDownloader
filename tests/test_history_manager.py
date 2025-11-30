import os
import sqlite3
import unittest
from pathlib import Path

from history_manager import DB_FILE, HistoryManager


class TestHistoryManager(unittest.TestCase):

    def setUp(self):
        # Use a temporary DB file for tests
        self.original_db_file = DB_FILE
        HistoryManager.DB_FILE = Path(
            "test_history.db"
        )  # Actually we need to patch the module level var or class usage
        # The class uses the module level var directly in _get_connection usually.
        # Let's patch _get_connection
        pass

    def tearDown(self):
        if Path("test_history.db").exists():
            os.remove("test_history.db")

    @unittest.mock.patch("history_manager.DB_FILE", Path("test_history.db"))
    def test_init_db(self):
        HistoryManager.init_db()
        self.assertTrue(Path("test_history.db").exists())

        # Verify schema
        conn = sqlite3.connect("test_history.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(history)")
        columns = [info[1] for info in cursor.fetchall()]
        self.assertIn("url", columns)
        self.assertIn("file_path", columns)
        conn.close()

    @unittest.mock.patch("history_manager.DB_FILE", Path("test_history.db"))
    def test_add_and_get_history(self):
        HistoryManager.init_db()
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
        self.assertEqual(history[0]["title"], "Test Title")
        self.assertEqual(history[0]["file_path"], "/tmp/file.mp4")

    @unittest.mock.patch("history_manager.DB_FILE", Path("test_history.db"))
    def test_clear_history(self):
        HistoryManager.init_db()
        HistoryManager.add_entry(
            "http://test", "Test", "/tmp", "mp4", "Completed", "10MB"
        )
        HistoryManager.clear_history()
        self.assertEqual(len(HistoryManager.get_history()), 0)

    @unittest.mock.patch("history_manager.DB_FILE", Path("test_history.db"))
    def test_migration(self):
        # Create old schema
        conn = sqlite3.connect("test_history.db")
        conn.execute(
            """
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                output_path TEXT,
                format_str TEXT,
                status TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_size TEXT
            )
        """
        )
        conn.commit()
        conn.close()

        # Run init_db which should migrate
        HistoryManager.init_db()

        conn = sqlite3.connect("test_history.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(history)")
        columns = [info[1] for info in cursor.fetchall()]
        self.assertIn("file_path", columns)
        conn.close()
