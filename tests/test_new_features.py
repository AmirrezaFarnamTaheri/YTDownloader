"""
Tests for new features added during the comprehensive audit.

Tests cover:
- Queue manager bulk operations (cancel_all, pause_all, resume_all, clear_completed)
- History manager search and filter functionality
- Dashboard view statistics
"""

import pytest


class TestQueueManagerBulkOperations:
    """Test cases for QueueManager bulk operations."""

    def test_cancel_all_cancels_active_downloads(self):
        """Test that cancel_all cancels all active downloads."""
        from queue_manager import QueueManager

        qm = QueueManager()
        # Add some items with different statuses
        qm.add_item({"url": "http://example.com/1", "status": "Downloading"})
        qm.add_item({"url": "http://example.com/2", "status": "Queued"})
        qm.add_item({"url": "http://example.com/3", "status": "Completed"})
        qm.add_item({"url": "http://example.com/4", "status": "Processing"})

        cancelled = qm.cancel_all()

        # Should have cancelled 3 items (Downloading, Queued, Processing)
        assert cancelled == 3

        items = qm.get_all()
        downloading_count = sum(1 for i in items if i["status"] == "Cancelled")
        assert downloading_count == 3
        # Completed should remain unchanged
        completed_count = sum(1 for i in items if i["status"] == "Completed")
        assert completed_count == 1

    def test_pause_all_pauses_queued_downloads(self):
        """Test that pause_all pauses all queued downloads."""
        from queue_manager import QueueManager

        qm = QueueManager()
        qm.add_item({"url": "http://example.com/1", "status": "Queued"})
        qm.add_item({"url": "http://example.com/2", "status": "Queued"})
        qm.add_item({"url": "http://example.com/3", "status": "Downloading"})

        paused = qm.pause_all()

        assert paused == 2
        items = qm.get_all()
        paused_count = sum(1 for i in items if i["status"] == "Paused")
        assert paused_count == 2

    def test_resume_all_resumes_paused_downloads(self):
        """Test that resume_all resumes all paused downloads."""
        from queue_manager import QueueManager

        qm = QueueManager()
        qm.add_item({"url": "http://example.com/1", "status": "Paused"})
        qm.add_item({"url": "http://example.com/2", "status": "Paused"})
        qm.add_item({"url": "http://example.com/3", "status": "Downloading"})

        resumed = qm.resume_all()

        assert resumed == 2
        items = qm.get_all()
        queued_count = sum(1 for i in items if i["status"] == "Queued")
        assert queued_count == 2

    def test_get_statistics_returns_correct_counts(self):
        """Test that get_statistics returns correct status counts."""
        from queue_manager import QueueManager

        qm = QueueManager()
        qm.add_item({"url": "http://example.com/1", "status": "Queued"})
        qm.add_item({"url": "http://example.com/2", "status": "Downloading"})
        qm.add_item({"url": "http://example.com/3", "status": "Completed"})
        qm.add_item({"url": "http://example.com/4", "status": "Error"})
        qm.add_item({"url": "http://example.com/5", "status": "Cancelled"})

        stats = qm.get_statistics()

        assert stats["total"] == 5
        assert stats["queued"] == 1
        assert stats["downloading"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["cancelled"] == 1

    def test_clear_completed_removes_finished_items(self):
        """Test that clear_completed removes completed, errored, and cancelled items."""
        from queue_manager import QueueManager

        qm = QueueManager()
        qm.add_item({"url": "http://example.com/1", "status": "Queued"})
        qm.add_item({"url": "http://example.com/2", "status": "Completed"})
        qm.add_item({"url": "http://example.com/3", "status": "Error"})
        qm.add_item({"url": "http://example.com/4", "status": "Cancelled"})
        qm.add_item({"url": "http://example.com/5", "status": "Downloading"})

        removed = qm.clear_completed()

        assert removed == 3
        items = qm.get_all()
        assert len(items) == 2
        # Only Queued and Downloading should remain
        statuses = {i["status"] for i in items}
        assert statuses == {"Queued", "Downloading"}


class TestHistoryManagerSearchFilter:
    """Test cases for HistoryManager search and filter functionality."""

    @pytest.fixture
    def setup_history(self, tmp_path):
        """Set up a temporary history database."""
        from history_manager import HistoryManager

        # Use a temporary database
        HistoryManager._test_db_file = (tmp_path / "test_history.db").resolve()
        HistoryManager.init_db()

        # Add some test entries
        manager = HistoryManager()
        manager.add_entry({
            "url": "https://youtube.com/watch?v=123",
            "title": "Test Video 1",
            "output_path": "/downloads",
            "format_str": "mp4",
            "status": "Completed",
            "file_size": "100MB",
        })
        manager.add_entry({
            "url": "https://youtube.com/watch?v=456",
            "title": "Another Video",
            "output_path": "/downloads",
            "format_str": "mp4",
            "status": "Completed",
            "file_size": "50MB",
        })
        manager.add_entry({
            "url": "https://vimeo.com/789",
            "title": "Vimeo Content",
            "output_path": "/downloads",
            "format_str": "webm",
            "status": "Error",
            "file_size": "0MB",
        })

        yield manager

        # Cleanup
        if hasattr(HistoryManager, "_test_db_file"):
            delattr(HistoryManager, "_test_db_file")

    def test_search_by_title(self, setup_history):
        """Test searching history by title."""
        result = setup_history.search_history("Test Video", search_in=["title"])

        assert result["total"] == 1
        assert len(result["entries"]) == 1
        assert result["entries"][0]["title"] == "Test Video 1"

    def test_search_by_url(self, setup_history):
        """Test searching history by URL."""
        result = setup_history.search_history("vimeo", search_in=["url"])

        assert result["total"] == 1
        assert len(result["entries"]) == 1
        assert "vimeo" in result["entries"][0]["url"]

    def test_search_both_fields(self, setup_history):
        """Test searching history in both title and URL."""
        result = setup_history.search_history("Video")

        # Should find both "Test Video 1" and "Another Video"
        assert result["total"] == 2

    def test_empty_search_returns_all(self, setup_history):
        """Test that empty search returns all entries."""
        result = setup_history.search_history("")

        assert result["total"] == 3

    def test_get_history_stats(self, setup_history):
        """Test getting history statistics."""
        stats = setup_history.get_history_stats()

        assert stats["total"] == 3
        assert "Completed" in stats["by_status"]
        assert stats["by_status"]["Completed"] == 2
        assert "Error" in stats["by_status"]
        assert stats["by_status"]["Error"] == 1

    def test_delete_entry(self, setup_history):
        """Test deleting a single history entry."""
        # Get all entries first
        entries = setup_history.get_history()
        first_entry_id = entries[0]["id"]

        deleted = setup_history.delete_entry(first_entry_id)

        assert deleted is True
        remaining = setup_history.get_history()
        assert len(remaining) == 2

    def test_export_history_json(self, setup_history):
        """Test exporting history as JSON."""
        result = setup_history.export_history("json")

        assert result is not None
        import json

        data = json.loads(result)
        assert len(data) == 3

    def test_export_history_csv(self, setup_history):
        """Test exporting history as CSV."""
        result = setup_history.export_history("csv")

        assert result is not None
        lines = result.strip().split("\n")
        # Header + 3 entries
        assert len(lines) == 4


class TestDownloaderModuleExports:
    """Test that the downloader module exports are correct."""

    def test_downloader_imports(self):
        """Test that key functions can be imported from downloader package."""
        from downloader import DownloadOptions, download_video, get_video_info

        assert callable(download_video)
        assert callable(get_video_info)
        assert DownloadOptions is not None


class TestViewsModuleExports:
    """Test that the views module exports are correct."""

    def test_views_imports(self):
        """Test that all views can be imported from views package."""
        from views import (
            BaseView,
            DashboardView,
            DownloadView,
            HistoryView,
            QueueView,
            RSSView,
            SettingsView,
        )

        assert BaseView is not None
        assert DashboardView is not None
        assert DownloadView is not None
        assert HistoryView is not None
        assert QueueView is not None
        assert RSSView is not None
        assert SettingsView is not None


class TestAppStateCleanup:
    """Test AppState cleanup functionality."""

    def test_cleanup_method_exists(self):
        """Test that AppState has a cleanup method."""
        from app_state import AppState

        state = AppState()
        assert hasattr(state, "cleanup")
        assert callable(state.cleanup)

    def test_cleanup_sets_shutdown_flag(self):
        """Test that cleanup sets the shutdown flag."""
        import threading

        from app_state import AppState

        state = AppState()
        # Replace mock with real Event if mocked
        if not isinstance(state.shutdown_flag, threading.Event):
            state.shutdown_flag = threading.Event()

        assert not state.shutdown_flag.is_set()

        state.cleanup()

        assert state.shutdown_flag.is_set()
