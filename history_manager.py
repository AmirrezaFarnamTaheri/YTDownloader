"""
History Manager.
Manages download history in a SQLite database.
"""

import csv
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, List

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manages the history of downloads using SQLite.
    """

    DB_FILE = os.path.expanduser("~/.streamcatch/history.db")
    MAX_DB_RETRIES = 3

    def __init__(self):
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        directory = os.path.dirname(self.DB_FILE)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as e:
                logger.error("Failed to create history DB directory: %s", e)

    def _resolve_db_file(self):
        """Allow overriding DB file for tests."""
        return getattr(self, "_test_db_file", self.DB_FILE)

    def _get_connection(self):
        db_file = self._resolve_db_file()
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        # Enable WAL for concurrency
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except sqlite3.Error:
            pass
        return conn

    def _init_db(self):
        """Initializes the database table."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        title TEXT,
                        status TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        filename TEXT,
                        filepath TEXT,
                        file_size TEXT
                    )
                """
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to initialize history DB: %s", e)

    def add_entry(self, entry: dict[str, Any]) -> None:
        """Adds a new entry to the history."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO history (url, title, status, filename, filepath, file_size)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        entry.get("url"),
                        entry.get("title"),
                        entry.get("status"),
                        entry.get("filename"),
                        entry.get("filepath"),
                        entry.get("file_size"),
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to add history entry: %s", e)

    def get_history(
        self, limit: int = 50, offset: int = 0, search_query: str = ""
    ) -> List[dict]:
        """Retrieves history entries."""
        try:
            with self._get_connection() as conn:
                if search_query:
                    query = """
                        SELECT * FROM history
                        WHERE title LIKE ? OR url LIKE ?
                        ORDER BY timestamp DESC LIMIT ? OFFSET ?
                    """
                    pattern = f"%{search_query}%"
                    cursor = conn.execute(query, (pattern, pattern, limit, offset))
                else:
                    query = (
                        "SELECT * FROM history ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                    )
                    cursor = conn.execute(query, (limit, offset))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to get history: %s", e)
            return []

    def clear_history(self) -> None:
        """Clears all history."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM history")
                conn.commit()
                # Vacuum to reclaim space
                conn.execute("VACUUM")
        except sqlite3.Error as e:
            logger.error("Failed to clear history: %s", e)

    def delete_entry(self, entry_id: int) -> None:
        """Deletes a specific entry."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to delete history entry: %s", e)

    def get_download_activity(self, days: int = 7) -> List[dict]:
        """
        Returns download count per day for the last N days.
        Used for dashboard charts.
        """
        activity = []
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Updated query to handle both text timestamps and unix epoch if any
            query = """
                SELECT
                    CASE
                        WHEN typeof(timestamp) IN ('integer', 'real') THEN date(timestamp, 'unixepoch')
                        ELSE date(timestamp)
                    END AS day,
                    COUNT(*)
                FROM history
                WHERE
                    CASE
                        WHEN typeof(timestamp) IN ('integer', 'real') THEN date(timestamp, 'unixepoch')
                        ELSE date(timestamp)
                    END >= date('now', ?)
                GROUP BY day
                ORDER BY day ASC
            """
            cursor.execute(query, (f"-{days} days",))

            rows = dict(cursor.fetchall())  # {date: count}

            # Fill in missing days with 0
            today = datetime.now().date()
            for i in range(days):
                d = (today - timedelta(days=days - 1 - i)).isoformat()
                count = rows.get(d, 0)
                # Helper for short day name
                day_name = (today - timedelta(days=days - 1 - i)).strftime("%a")
                activity.append(
                    {"date": d, "count": count, "label": day_name[0]}
                )  # M, T, W

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error getting activity stats: %s", e)
            # Return empty structure on failure
            activity = [{"date": "", "count": 0, "label": ""} for _ in range(days)]
        finally:
            if conn:
                conn.close()

        return activity

    def get_stats(self) -> dict:
        """Returns overall stats."""
        stats = {"total_downloads": 0, "total_size_mb": 0}
        try:
            with self._get_connection() as conn:
                # Total count
                cursor = conn.execute("SELECT COUNT(*) FROM history")
                stats["total_downloads"] = cursor.fetchone()[0]

                # Total size (approx, parsing strings might be hard if format varies)
                # We stored file_size as string "XX MB".
                # For accurate stats we should store bytes in future.
                # Here we just count entries for now.
        except sqlite3.Error:
            pass
        return stats

    def export_to_json(self, filepath: str):
        """Exports history to JSON."""
        data = self.get_history(limit=10000)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def export_to_csv(self, filepath: str):
        """Exports history to CSV."""
        data = self.get_history(limit=10000)
        if not data:
            return

        keys = data[0].keys()
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)

    def vacuum(self):
        """Optimizes the database."""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
        except sqlite3.Error as e:
            logger.warning("Failed to vacuum DB: %s", e)
