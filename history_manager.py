"""
History manager for persistent storage of download history.
"""

import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# DB file path with fallback for mobile/sandboxed environments
try:
    DB_FILE = Path.home() / ".streamcatch" / "history.db"
    # Ensure directory exists immediately if possible
    try:
        if not DB_FILE.parent.exists():
            DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
except Exception: # pylint: disable=broad-exception-caught
    DB_FILE = Path("history.db")


class HistoryManager:
    """
    Manages download history using SQLite with robust validation, connection pooling (conceptually),
    and error handling. Thread-safe operations.
    """

    MAX_DB_RETRIES = 3
    DB_RETRY_DELAY = 0.5  # seconds

    @staticmethod
    def _resolve_db_file() -> Path:
        """Return the configured DB path."""
        # Use module level DB_FILE but allow for testing overrides via class attribute if needed
        return getattr(HistoryManager, "DB_FILE", DB_FILE)

    @staticmethod
    def _get_connection(timeout: float = 5.0) -> sqlite3.Connection:
        """
        Get database connection with timeout.
        Returns a raw connection object which should be used in a with block or closed manually.
        """
        db_file = HistoryManager._resolve_db_file()

        # Ensure directory exists (redundant check for robustness)
        try:
            if not db_file.parent.exists():
                db_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Fallback to local if home is not writable
            if db_file != Path("history.db"):
                db_file = Path("history.db")

        conn = sqlite3.connect(str(db_file), timeout=timeout)

        # Enable WAL mode for better concurrency
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL") # Performance tweak
        except sqlite3.Error as e:
            logger.warning("Failed to set PRAGMA options: %s", e)

        return conn

    @staticmethod
    def _validate_input(url: str, title: str, output_path: str) -> None:
        """
        Validate inputs to prevent injection and ensure data integrity.
        """
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")
        if len(url) > 2048:
            raise ValueError("URL too long")

        # Prevent null bytes
        if "\x00" in url or (title and "\x00" in title) or (
            output_path and "\x00" in output_path
        ):
            raise ValueError("Null bytes not allowed")

    @staticmethod
    def init_db():
        """Initialize the history database table and perform migrations."""
        logger.info("Initializing history database...")

        retry_count = 0
        last_error = None

        while retry_count < HistoryManager.MAX_DB_RETRIES:
            conn = None
            try:
                conn = HistoryManager._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        title TEXT,
                        output_path TEXT,
                        format_str TEXT,
                        status TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        file_size TEXT,
                        file_path TEXT
                    )
                    """
                )

                # Migration Check: file_path column
                # Get current columns
                cursor.execute("PRAGMA table_info(history)")
                columns = [row[1] for row in cursor.fetchall()]

                if "file_path" not in columns:
                    logger.info("Migrating DB: Adding file_path column")
                    cursor.execute("ALTER TABLE history ADD COLUMN file_path TEXT")

                # Ensure indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_status ON history(status)"
                )

                conn.commit()
                logger.info("History database initialized.")
                return

            except sqlite3.OperationalError as e:
                last_error = e
                if "locked" in str(e).lower():
                    retry_count += 1
                    logger.warning(
                        "DB locked during init, retrying (%d/%d)...",
                        retry_count,
                        HistoryManager.MAX_DB_RETRIES
                    )
                    time.sleep(HistoryManager.DB_RETRY_DELAY)
                    continue
                logger.error("Failed to init history DB: %s", e)
                raise e # Re-raise other operational errors
            except Exception as e:
                logger.error("Failed to init history DB (General): %s", e)
                raise # Re-raise for visibility
            finally:
                if conn:
                    conn.close()

        # If we exhausted retries
        if last_error:
            raise last_error

    @staticmethod
    def add_entry(
        url: str,
        title: str,
        output_path: str,
        format_str: str,
        status: str,
        file_size: str,
        file_path: Optional[str] = None,
    ):
        """Add a new entry to the history."""
        # pylint: disable=too-many-arguments
        HistoryManager._validate_input(url, title or "", output_path or "")

        retry_count = 0
        last_error = None

        while retry_count < HistoryManager.MAX_DB_RETRIES:
            conn = None
            try:
                conn = HistoryManager._get_connection()
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()

                cursor.execute(
                    """
                    INSERT INTO history
                    (url, title, output_path, format_str, status, timestamp, file_size, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url, title, output_path, format_str, status,
                        timestamp, file_size, file_path
                    )
                )
                conn.commit()
                return

            except sqlite3.OperationalError as e:
                last_error = e
                if "locked" in str(e).lower():
                    retry_count += 1
                    logger.warning(
                        "DB locked during add_entry, retrying (%d/%d)...",
                        retry_count,
                        HistoryManager.MAX_DB_RETRIES
                    )
                    time.sleep(HistoryManager.DB_RETRY_DELAY)
                    continue
                logger.error("DB Error in add_entry: %s", e)
                break # Don't retry non-locked errors indefinitely
            except Exception as e:
                logger.error("Error in add_entry: %s", e)
                raise e # Re-raise
            finally:
                if conn:
                    conn.close()

        # Raise if exhausted
        if retry_count >= HistoryManager.MAX_DB_RETRIES and last_error:
            raise last_error

    @staticmethod
    def get_history_paginated(offset: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Retrieve history entries with pagination."""
        conn = None
        entries = []
        total = 0

        try:
            conn = HistoryManager._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM history")
            result = cursor.fetchone()
            total = result[0] if result else 0

            cursor.execute(
                "SELECT * FROM history ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()
            entries = [dict(row) for row in rows]

        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Error retrieving history: %s", e)
        finally:
            if conn:
                conn.close()

        return {
            "entries": entries,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }

    @staticmethod
    def get_history(limit: int = 100) -> List[Dict[str, Any]]:
        """
        Simple retrieval of recent history.
        Wrapper around paginated method for backward compatibility/ease of use.
        """
        result = HistoryManager.get_history_paginated(offset=0, limit=limit)
        return result.get("entries", [])

    @staticmethod
    def clear_history():
        """Clear all history."""
        try:
            # Replaced direct sqlite3.connect with _get_connection for consistency
            conn = HistoryManager._get_connection()
            try:
                conn.execute("DELETE FROM history")
                conn.commit()
                conn.execute("VACUUM")
            finally:
                conn.close()

            logger.info("History cleared.")
        except Exception as e:
            logger.error("Failed to clear history: %s", e)
            raise e # Raise to satisfy tests expecting errors on failure
