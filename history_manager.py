import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DB_FILE = Path.home() / '.ytdownloader' / 'history.db'

class HistoryManager:
    """Manages download history using SQLite."""

    @staticmethod
    def _get_connection():
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(DB_FILE)

    @staticmethod
    def init_db():
        """Initialize the history database table."""
        try:
            with HistoryManager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        title TEXT,
                        output_path TEXT,
                        format_str TEXT,
                        status TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        file_size TEXT
                    )
                ''')
                conn.commit()
            logger.info("History database initialized.")
        except Exception as e:
            logger.error(f"Failed to init history DB: {e}")

    @staticmethod
    def add_entry(url: str, title: str, output_path: str, format_str: str, status: str, file_size: str):
        """Add a new entry to the history."""
        try:
            with HistoryManager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO history (url, title, output_path, format_str, status, timestamp, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (url, title, output_path, format_str, status, datetime.now(), file_size))
                conn.commit()
            logger.debug(f"Added history entry: {title}")
        except Exception as e:
            logger.error(f"Failed to add history entry: {e}")

    @staticmethod
    def get_history(limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve history entries."""
        entries = []
        try:
            with HistoryManager._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM history ORDER BY timestamp DESC LIMIT ?', (limit,))
                rows = cursor.fetchall()
                for row in rows:
                    entries.append(dict(row))
        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}")
        return entries

    @staticmethod
    def clear_history():
        """Clear all history."""
        try:
            with HistoryManager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM history')
                conn.commit()
            logger.info("History cleared.")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
