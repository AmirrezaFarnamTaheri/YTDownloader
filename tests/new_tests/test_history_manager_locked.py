import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from history_manager import HistoryManager


def test_init_db_locked_failure():
    """Test that init_db raises after max retries when database is locked."""
    with patch("history_manager.HistoryManager._get_connection") as mock_conn:
        mock_conn.side_effect = sqlite3.OperationalError("database is locked")

        # Override retry delay to speed up test
        original_delay = HistoryManager.DB_RETRY_DELAY
        HistoryManager.DB_RETRY_DELAY = 0.01

        try:
            with pytest.raises(sqlite3.OperationalError) as exc_info:
                HistoryManager.init_db()
            assert "database is locked" in str(exc_info.value)
            assert mock_conn.call_count == HistoryManager.MAX_DB_RETRIES
        finally:
            HistoryManager.DB_RETRY_DELAY = original_delay


def test_add_entry_locked_failure():
    """Test that add_entry raises after max retries when database is locked."""
    with patch("history_manager.HistoryManager._get_connection") as mock_conn:
        mock_conn.side_effect = sqlite3.OperationalError("database is locked")

        original_delay = HistoryManager.DB_RETRY_DELAY
        HistoryManager.DB_RETRY_DELAY = 0.01

        try:
            with pytest.raises(sqlite3.OperationalError) as exc_info:
                HistoryManager.add_entry(
                    "http://example.com", "Title", "/path", "mp4", "done", "10MB"
                )
            assert "database is locked" in str(exc_info.value)
            assert mock_conn.call_count == HistoryManager.MAX_DB_RETRIES
        finally:
            HistoryManager.DB_RETRY_DELAY = original_delay
