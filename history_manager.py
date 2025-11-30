import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_FILE = Path.home() / ".streamcatch" / "history.db"


class HistoryManager:
    """Manages download history using SQLite with validation and error handling."""

    # Maximum retries for database lock
    MAX_DB_RETRIES = 3  # Reduced to fail faster
    DB_RETRY_DELAY = 0.5  # seconds
    DB_INIT_TIMEOUT = 10.0  # Maximum time for any DB operation

    @staticmethod
    def _resolve_db_file() -> Path:
        """Return the configured DB path, supporting test overrides."""
        return getattr(HistoryManager, "DB_FILE", DB_FILE)

    class _ConnectionWrapper:
        """Ensures sqlite connections are closed even when __exit__ doesn't."""

        def __init__(self, conn):
            self._conn = conn

        def __enter__(self):
            return (
                self._conn.__enter__()
                if hasattr(self._conn, "__enter__")
                else self._conn
            )

        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                if hasattr(self._conn, "__exit__"):
                    self._conn.__exit__(exc_type, exc_val, exc_tb)
            finally:
                try:
                    self._conn.close()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Failed to close history DB connection: %s", exc)

    @staticmethod
    def _get_connection(timeout: float = 5.0):  # Reduced timeout
        """
        Get database connection with timeout and ensure it closes cleanly.

        Args:
            timeout: Maximum time to wait for database lock (seconds)

        Returns:
            Context manager that yields a sqlite3.Connection
        """
        db_file = HistoryManager._resolve_db_file()
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if DB file is already locked by another process
        if db_file.exists() and not os.access(db_file, os.W_OK):
            raise sqlite3.OperationalError(f"Database file not writable: {db_file}")

        conn = sqlite3.connect(db_file, timeout=timeout)
        logger.debug(f"Opened DB connection to {db_file} (Timeout: {timeout}s)")
        # Enable WAL mode for better concurrency
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception as e:
            logger.warning(f"Failed to enable WAL mode: {e}")
        return HistoryManager._ConnectionWrapper(conn)

    @staticmethod
    def _validate_input(url: str, title: str, output_path: str) -> None:
        """
        Validate inputs to prevent injection and ensure data integrity.

        Args:
            url: URL to validate
            title: Title to validate
            output_path: Path to validate

        Raises:
            ValueError: If validation fails
        """
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")
        if len(url) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        if title and len(title) > 500:
            raise ValueError("Title too long (max 500 characters)")
        if output_path and len(output_path) > 1024:
            raise ValueError("Output path too long (max 1024 characters)")
        # Prevent null bytes (SQL injection vector)
        if (
            "\x00" in url
            or (title and "\x00" in title)
            or (output_path and "\x00" in output_path)
        ):
            raise ValueError("Null bytes not allowed in inputs")

        # Additional SQL injection prevention
        dangerous_patterns = [
            "';",
            '";',
            "--",
            "/*",
            "*/",
            "xp_",
            "sp_",
            "EXEC",
            "EXECUTE",
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "UNION",
            "SELECT",
        ]

        for pattern in dangerous_patterns:
            if pattern.lower() in url.lower():
                logger.warning(f"Potentially dangerous pattern in URL: {pattern}")
                # Don't block - yt-dlp might need these in query strings
                break
            if title and pattern.lower() in title.lower():
                raise ValueError(f"Dangerous pattern not allowed in title: {pattern}")
            if output_path and pattern.lower() in output_path.lower():
                raise ValueError(f"Dangerous pattern not allowed in path: {pattern}")

        # Validate URL format
        if not url.startswith(("http://", "https://", "ftp://", "ftps://")):
            raise ValueError(
                "URL must start with http://, https://, ftp://, or ftps://"
            )

    @staticmethod
    def init_db():
        """Initialize the history database table and perform migrations."""
        retry_count = 0
        last_error = None

        logger.info(
            f"Initializing history database at {HistoryManager._resolve_db_file()}"
        )

        while retry_count < HistoryManager.MAX_DB_RETRIES:
            try:
                with HistoryManager._get_connection() as conn:
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
                            file_size TEXT
                        )
                    """
                    )

                    # Migration: Check for file_path column
                    cursor.execute("PRAGMA table_info(history)")
                    columns = [info[1] for info in cursor.fetchall()]
                    if "file_path" not in columns:
                        logger.info("Migrating database: Adding file_path column")
                        cursor.execute("ALTER TABLE history ADD COLUMN file_path TEXT")

                    # Create indexes for better query performance
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)"
                    )
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_history_status ON history(status)"
                    )
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_history_url ON history(url)"
                    )

                    conn.commit()
                logger.info("History database initialized with indexes.")
                return  # Success

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    last_error = e
                    retry_count += 1
                    if retry_count < HistoryManager.MAX_DB_RETRIES:
                        logger.warning(
                            f"Database locked during init, retrying ({retry_count}/{HistoryManager.MAX_DB_RETRIES})..."
                        )
                        time.sleep(HistoryManager.DB_RETRY_DELAY * retry_count)
                    else:
                        logger.error(
                            f"Failed to init history DB after {retry_count} retries: {e}", exc_info=True
                        )
                        raise
                else:
                    logger.error(f"Failed to init history DB: {e}", exc_info=True)
                    raise
            except Exception as e:
                logger.error(f"Failed to init history DB: {e}", exc_info=True)
                raise

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
        """
        Add a new entry to the history with validation and retry logic.

        Args:
            url: Source URL
            title: Download title
            output_path: Output directory
            format_str: Format string used
            status: Download status
            file_size: File size string
            file_path: Full path to downloaded file

        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        HistoryManager._validate_input(url, title or "", output_path or "")

        retry_count = 0
        last_error = None

        while retry_count < HistoryManager.MAX_DB_RETRIES:
            try:
                with HistoryManager._get_connection() as conn:
                    cursor = conn.cursor()
                    timestamp_str = datetime.now().isoformat()
                    cursor.execute(
                        """
                        INSERT INTO history (url, title, output_path, format_str, status, timestamp, file_size, file_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            url,
                            title,
                            output_path,
                            format_str,
                            status,
                            timestamp_str,
                            file_size,
                            file_path,
                        ),
                    )
                    conn.commit()
                logger.debug(f"Added history entry: {title} (ID: {cursor.lastrowid})")
                return  # Success

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    last_error = e
                    retry_count += 1
                    if retry_count < HistoryManager.MAX_DB_RETRIES:
                        logger.warning(
                            f"Database locked during add, retrying ({retry_count}/{HistoryManager.MAX_DB_RETRIES})..."
                        )
                        time.sleep(HistoryManager.DB_RETRY_DELAY * retry_count)
                    else:
                        logger.error(
                            f"Failed to add history entry after {retry_count} retries: {e}", exc_info=True
                        )
                        raise
                else:
                    logger.error(f"Failed to add history entry: {e}", exc_info=True)
                    raise
            except Exception as e:
                logger.error(f"Failed to add history entry: {e}", exc_info=True)
                raise

        if last_error:
            raise last_error

    @staticmethod
    def get_history(limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve history entries."""
        entries = []
        try:
            logger.debug(f"Fetching history (limit={limit})")
            start_time = time.time()
            with HistoryManager._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM history ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
                rows = cursor.fetchall()
                for row in rows:
                    entries.append(dict(row))
            elapsed = time.time() - start_time
            logger.debug(f"Retrieved {len(entries)} history entries in {elapsed:.4f}s")
        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}", exc_info=True)
        return entries

    @staticmethod
    def get_history_paginated(offset: int = 0, limit: int = 50) -> Dict[str, Any]:
        """
        Retrieve history entries with pagination.

        Returns:
            Dict with 'entries', 'total', 'offset', 'limit'
        """
        entries = []
        total = 0

        try:
            with HistoryManager._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get total count
                cursor.execute("SELECT COUNT(*) FROM history")
                total = cursor.fetchone()[0]

                # Get paginated results
                cursor.execute(
                    "SELECT * FROM history ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                rows = cursor.fetchall()
                for row in rows:
                    entries.append(dict(row))

            logger.debug(f"Paginated history: offset={offset}, limit={limit}, fetched={len(entries)}, total={total}")

        except Exception as e:
            logger.error(f"Failed to retrieve paginated history: {e}", exc_info=True)

        return {
            "entries": entries,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total,
        }

    @staticmethod
    def clear_history():
        """Clear all history."""
        try:
            logger.info("Clearing download history...")
            with HistoryManager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM history")
                conn.commit()

            # Vacuum must be done outside of transaction or with autocommit.
            # _get_connection uses default isolation (implicit transaction).
            # We need to run VACUUM in a separate step with isolation_level=None

            db_file = HistoryManager._resolve_db_file()
            # Brief connection just for VACUUM
            with sqlite3.connect(db_file, isolation_level=None) as vac_conn:
                vac_conn.execute("VACUUM")

            logger.info("History cleared successfully.")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}", exc_info=True)
