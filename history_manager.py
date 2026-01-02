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

    @classmethod
    def init_db(cls):
        """Initializes the database table and handles migrations."""
        db_file = getattr(cls, "_test_db_file", cls.DB_FILE)

        try:
            directory = os.path.dirname(db_file)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            with sqlite3.connect(db_file) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()

                # Check if table exists
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='history'"
                )
                table_exists = cursor.fetchone()

                if not table_exists:
                    # Create new table
                    cursor.execute(
                        """
                        CREATE TABLE history (
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
                else:
                    # Perform migration if necessary
                    cursor.execute("PRAGMA table_info(history)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if "output_path" in columns and "filepath" not in columns:
                        logger.info("Migrating history database schema...")
                        # Rename old columns and add new ones
                        cursor.execute(
                            "ALTER TABLE history RENAME COLUMN output_path TO filepath"
                        )
                        if "filename" not in columns:
                            cursor.execute(
                                "ALTER TABLE history ADD COLUMN filename TEXT"
                            )

                # Ensure indexes exist
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)"
                )
                conn.commit()

        except OSError as e:
            logger.error("Failed to create history DB directory: %s", e)
        except sqlite3.Error as e:
            logger.error("Failed to initialize/migrate history DB: %s", e)

    def _init_db(self):
        """Instance level init (for backward compat if needed, or delegation)."""
        HistoryManager.init_db()

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

            # Vacuum must run outside an active transaction
            db_file = self._resolve_db_file()
            with sqlite3.connect(db_file, isolation_level=None) as conn:
                conn.execute("VACUUM")
        except sqlite3.Error as e:
            logger.error("Failed to clear history: %s", e)

    def delete_entry(self, entry_id: int) -> bool:
        """Deletes a specific entry."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
                conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Failed to delete history entry: %s", e)
            return False

    def search_history(self, query: str, search_in: list[str] | None = None) -> dict:
        """Search history with filters."""
        if not search_in:
            search_in = ["title", "url"]

        try:
            with self._get_connection() as conn:
                sql = "SELECT * FROM history"
                params: List[Any] = []
                if query:
                    conditions = []
                    for field in search_in:
                        conditions.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")
                    sql += " WHERE " + " OR ".join(conditions)

                sql += " ORDER BY timestamp DESC"

                cursor = conn.execute(sql, params)
                rows = [dict(row) for row in cursor.fetchall()]
                return {"total": len(rows), "entries": rows}
        except sqlite3.Error as e:
            logger.error("Failed to search history: %s", e)
            return {"total": 0, "entries": []}

    def get_history_stats(self) -> dict:
        """Get statistics by status."""
        stats = {"total": 0, "by_status": {}}
        try:
            with self._get_connection() as conn:
                # Total
                cursor = conn.execute("SELECT COUNT(*) FROM history")
                result = cursor.fetchone()
                stats["total"] = result[0] if result else 0

                # By status
                cursor = conn.execute(
                    "SELECT status, COUNT(*) FROM history GROUP BY status"
                )
                for row in cursor.fetchall():
                    stats["by_status"][row["status"]] = row[1]
        except sqlite3.Error as e:
            logger.error("Failed to get history stats: %s", e)
        return stats

    def export_history(self, format_type: str = "json") -> str | None:
        """Export history to string."""
        data = self.get_history(limit=10000)
        if format_type == "json":
            return json.dumps(data, indent=2, default=str)
        elif format_type == "csv":
            import io

            if not data:
                return ""
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()
        return None

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
