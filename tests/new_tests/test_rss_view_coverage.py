"""
Tests for RSSView coverage.
"""

from unittest.mock import MagicMock, patch

import flet as ft

from localization_manager import LocalizationManager
from views.rss_view import RSSView


def test_rss_view_tab_change():
    """Test tab switching logic."""
    view = RSSView({"rss_feeds": []})
    view.update = MagicMock()
    view.refresh_feeds = MagicMock()

    # Switch to second tab (index 1)
    view.tabs.selected_index = 1
    view.on_tab_change(None)

    # Layout uses Tabs now, content visibility is handled by Tab control internally
    # We can check if refresh_feeds was called if list is empty
    view.refresh_feeds.assert_called()


def test_rss_view_fetch_task_exception():
    """Test feed fetching with one bad feed."""
    view = RSSView({"rss_feeds": ["http://good.com", "http://bad.com"]})
    view.update = MagicMock()

    # Mock page for clipboard access in item creation (though not called here)
    view.page = MagicMock()

    with patch("rss_manager.RSSManager.get_aggregated_items") as mock_agg:
        mock_agg.return_value = [
            {
                "title": "Video 1",
                "link": "http://v1",
                "published": "2023-01-01",
                "feed_name": "Good Feed",
                "date_obj": None,
            }
        ]
        view._fetch_feeds_task()
        assert len(view.items_list.controls) == 1


def test_rss_view_fetch_task_empty():
    """Test fetch task with no items."""
    view = RSSView({"rss_feeds": ["http://empty.com"]})
    view.update = MagicMock()

    # Pre-load "no_items_found"
    LocalizationManager._strings = {"no_items_found": "No items found."}

    # Patch get_aggregated_items to avoid thread pool
    with patch("rss_manager.RSSManager.get_aggregated_items", return_value=[]):
        view._fetch_feeds_task()

        assert len(view.items_list.controls) == 1
        assert "No items found" in view.items_list.controls[0].value


def test_rss_view_item_copy():
    """Test item interaction."""
    view = RSSView({"rss_feeds": ["http://test.com"]})
    view.update = MagicMock()
    view.page = MagicMock()

    with patch(
        "rss_manager.RSSManager.get_aggregated_items",
        return_value=[
            {
                "title": "T",
                "link": "L",
                "published": "D",
                "feed_name": "Test Feed",
                "date_obj": None,
            }
        ],
    ):
        view._fetch_feeds_task()

        # Get the item control
        # Card -> Container -> Column -> Row -> Button
        card = view.items_list.controls[0]
        # Just verify it exists
        assert isinstance(card, ft.Card)
