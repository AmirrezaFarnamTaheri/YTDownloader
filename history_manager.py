"""
History Manager.
Manages download history in a SQLite database.
"""

import csv
import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app_paths import data_file

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manages the history of downloads using SQLite.
    """

    DB_FILE = str(data_file("history.db"))
    MAX_DB_RETRIES = 3
    #: Upper bound for an imported history file (5 MB ≈ tens of thousands of rows).
    MAX_IMPORT_BYTES = 5 * 1024 * 1024

    _db_initialized: bool = False
    _db_init_lock = threading.Lock()

    def __init__(self):
        self._ensure_db_dir()
        # Ensure schema exists once across all instances/threads
        HistoryManager._ensure_schema(self._resolve_db_file())

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
    def _ensure_schema(cls, db_file: str):
        """Idempotent one-time schema initialization guarded by a process lock."""
        # Instance attribute shortcut for backward compatibility
        with cls._db_init_lock:
            if cls._db_initialized and db_file == cls.DB_FILE:
                return
            cls._create_schema(db_file)
            if db_file == cls.DB_FILE:
                cls._db_initialized = True

    @classmethod
    def init_db(cls):
        """Initializes the database table and handles migrations (idempotent)."""
        db_file = getattr(cls, "_test_db_file", cls.DB_FILE)
        cls._ensure_schema(db_file)

    @staticmethod
    def _create_schema(db_file: str):
        """Create/migrate the history schema in the given db file."""

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
                    cursor.execute("""
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
                        """)
                else:
                    # Perform migration if necessary
                    cursor.execute("PRAGMA table_info(history)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if "output_path" in columns and "filepath" not in columns:
                        logger.info("Migrating history database schema...")
                        # Use copy-swap method for broader compatibility
                        cursor.execute("""
                            CREATE TABLE history_new (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                url TEXT NOT NULL,
                                title TEXT,
                                status TEXT,
                                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                                filename TEXT,
                                filepath TEXT,
                                file_size TEXT
                            )
                            """)
                        # Copy data, mapping output_path to filepath
                        # We assume file_size exists in old schema as per usage
                        cursor.execute("""
                            INSERT INTO history_new (id, url, title, status, timestamp, filepath, file_size)
                            SELECT id, url, title, status, timestamp, output_path, file_size
                            FROM history
                            """)
                        cursor.execute("DROP TABLE history")
                        cursor.execute("ALTER TABLE history_new RENAME TO history")

                # Ensure indexes exist
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_status ON history(status)"
                )
                conn.commit()

        except OSError as e:
            logger.error("Failed to create history DB directory: %s", e)
        except sqlite3.Error as e:
            logger.error("Failed to initialize/migrate history DB: %s", e)

    def add_entry(self, entry: dict[str, Any]) -> None:
        """Adds a new entry to the history.

        ``timestamp`` is optional: downloads use the database default, while
        imported history keeps the original moment of the download.
        """
        if not entry.get("url") or not entry.get("status"):
            logger.warning("Ignoring incomplete history entry: %s", entry)
            return

        try:
            with self._get_connection() as conn:
                timestamp = entry.get("timestamp")
                if timestamp:
                    conn.execute(
                        """
                        INSERT INTO history
                            (url, title, status, timestamp, filename, filepath, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry.get("url"),
                            entry.get("title"),
                            entry.get("status"),
                            timestamp,
                            entry.get("filename"),
                            entry.get("filepath"),
                            entry.get("file_size"),
                        ),
                    )
                else:
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
    ) -> list[dict]:
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
            self.vacuum()
        except sqlite3.Error as e:
            logger.error("Failed to clear history: %s", e)

    def delete_entry(self, entry_id: int) -> bool:
        """Deletes a specific entry."""
        return self.delete_entries([entry_id])

    def delete_entries(self, entry_ids: list[int]) -> bool:
        """Deletes multiple entries by ID."""
        if not entry_ids:
            return False
        try:
            with self._get_connection() as conn:
                # Use parameterized query with 'IN' clause
                placeholders = ",".join("?" * len(entry_ids))
                sql = f"DELETE FROM history WHERE id IN ({placeholders})"
                conn.execute(sql, entry_ids)
                conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Failed to delete history entries: %s", e)
            return False

    def search_history(self, query: str, search_in: list[str] | None = None) -> dict:
        """Search history with filters."""
        if not search_in:
            search_in = ["title", "url"]

        # Whitelist fields to prevent SQL injection
        valid_fields = {"url", "title", "status", "filename", "filepath"}
        search_in = [f for f in search_in if f in valid_fields]
        if not search_in:
            search_in = ["title", "url"]

        try:
            with self._get_connection() as conn:
                sql = "SELECT * FROM history"
                params: list[Any] = []
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
        stats: dict[str, Any] = {"total": 0, "by_status": {}}
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
        if format_type == "csv":
            import io

            if not data:
                return ""
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()
        return None

    def get_download_activity(self, days: int = 7) -> list[dict]:
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

    #: ``file_size`` has been stored in two shapes over the project's life:
    #: raw byte counts (yt-dlp reports) and pre-formatted strings such as
    #: ``"12.50 MB"`` (``format_file_size``). Both are understood here.
    _SIZE_UNITS = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
        "PB": 1024**5,
    }

    @classmethod
    def _parse_size_bytes(cls, value: Any) -> int:
        """Return the byte count encoded in a stored ``file_size`` value.

        Unknown or unparsable values yield ``0`` so that aggregates stay
        usable instead of failing on a single malformed row.
        """
        if value is None:
            return 0
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return max(0, int(value))

        text = str(value).strip().upper()
        if not text or text in {"N/A", "NONE", "UNKNOWN"}:
            return 0

        match = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*([KMGTP]?I?B)?", text)
        if not match:
            return 0
        number = float(match.group(1))
        unit = (match.group(2) or "B").replace("I", "")  # KiB -> KB, MiB -> MB, ...
        return int(number * cls._SIZE_UNITS.get(unit, 1))

    def get_stats(self) -> dict:
        """Returns overall stats: entry count and cumulative size in MB."""
        stats: dict[str, Any] = {"total_downloads": 0, "total_size_mb": 0}
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM history")
                stats["total_downloads"] = int(cursor.fetchone()[0])

                cursor = conn.execute("SELECT file_size FROM history")
                total_bytes = sum(
                    self._parse_size_bytes(row[0]) for row in cursor.fetchall()
                )
                stats["total_size_mb"] = round(total_bytes / (1024**2), 2)
        except sqlite3.Error as e:
            logger.warning("Failed to get aggregate history stats: %s", e)
        return stats

    def import_entries(self, entries: Any) -> tuple[int, int]:
        """Import entries produced by :meth:`export_history`.

        Returns ``(imported, skipped)``. Entries already present, identified by
        ``(url, timestamp)``, are skipped so importing the same file twice does
        not duplicate history. Malformed rows are skipped rather than aborting
        the whole import.
        """
        if not isinstance(entries, list):
            logger.warning("History import payload is not a list: %s", type(entries))
            return 0, 0

        existing: set[tuple[str, str]] = set()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT url, timestamp FROM history")
                existing = {(str(row[0]), str(row[1])) for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error("Failed to read history for import: %s", e)
            return 0, 0

        imported = 0
        skipped = 0
        for raw in entries:
            if not isinstance(raw, dict) or not raw.get("url") or not raw.get("status"):
                skipped += 1
                continue

            key = (str(raw.get("url")), str(raw.get("timestamp")))
            if key in existing:
                skipped += 1
                continue

            entry = {
                "url": raw.get("url"),
                "title": raw.get("title"),
                "status": raw.get("status"),
                "filename": raw.get("filename"),
                "filepath": raw.get("filepath"),
                "file_size": raw.get("file_size"),
            }
            # Only carry a timestamp across when the export had a real one.
            if raw.get("timestamp"):
                entry["timestamp"] = raw["timestamp"]

            self.add_entry(entry)
            existing.add(key)
            imported += 1

        logger.info("History import: %d imported, %d skipped", imported, skipped)
        return imported, skipped

    def import_from_json_file(self, filepath: str) -> tuple[int, int]:
        """Import a JSON file previously written by :meth:`export_to_json`.

        The size cap is checked before reading so a misplaced large file cannot
        exhaust memory.
        """
        path = Path(filepath)
        try:
            size = int(path.stat().st_size)
        except (OSError, TypeError, ValueError) as e:
            raise ValueError(f"History file is not readable: {e}") from e

        if size > self.MAX_IMPORT_BYTES:
            raise ValueError(
                f"History file is larger than {self.MAX_IMPORT_BYTES // (1024 * 1024)} MB"
            )

        with open(path, encoding="utf-8") as handle:
            try:
                payload = json.load(handle)
            except json.JSONDecodeError as e:
                raise ValueError(f"History file is not valid JSON: {e}") from e

        if isinstance(payload, dict) and isinstance(payload.get("history"), list):
            payload = payload["history"]

        return self.import_entries(payload)

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
            db_file = self._resolve_db_file()
            # Connect with isolation_level=None to ensure VACUUM runs outside a transaction
            with sqlite3.connect(db_file, isolation_level=None) as conn:
                conn.execute("VACUUM")
        except sqlite3.Error as e:
            logger.warning("Failed to vacuum DB: %s", e)
