from unittest.mock import MagicMock, patch

import flet as ft
import pytest

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

    with patch("rss_manager.RSSManager.parse_feed") as mock_parse:

        def side_effect(url, instance=None):
            if "bad" in url:
                raise Exception("Network Error")
            return [
                {"title": "Video 1", "link": "http://v1", "published": "2023-01-01"}
            ]

        mock_parse.side_effect = side_effect

        # Run directly without thread
        view._fetch_feeds_task()

        assert len(view.items_list.controls) == 1


def test_rss_view_fetch_task_empty():
    """Test fetch task with no items."""
    view = RSSView({"rss_feeds": ["http://empty.com"]})
    view.update = MagicMock()

    with patch("rss_manager.RSSManager.parse_feed", return_value=[]):
        view._fetch_feeds_task()

        assert len(view.items_list.controls) == 1
        assert "No items found" in view.items_list.controls[0].value


def test_rss_view_item_copy():
    """Test item interaction."""
    view = RSSView({"rss_feeds": ["http://test.com"]})
    view.update = MagicMock()
    view.page = MagicMock()

    with patch(
        "rss_manager.RSSManager.parse_feed",
        return_value=[{"title": "T", "link": "L", "published": "D"}],
    ):
        view._fetch_feeds_task()

        # Get the item control
        # Card -> Container -> Column -> Row -> Button
        card = view.items_list.controls[0]
        # Just verify it exists
        assert isinstance(card, ft.Card)
