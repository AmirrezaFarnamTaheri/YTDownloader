import flet as ft
import pytest
from unittest.mock import MagicMock, patch
from views.rss_view import RSSView


def test_rss_view_tab_change():
    """Test tab switching logic."""
    view = RSSView({"rss_feeds": []})
    view.update = MagicMock()
    view.refresh_feeds = MagicMock()

    # Switch to second tab (index 1)
    view.tabs.selected_index = 1
    view.on_tab_change(None)

    assert view.feeds_content.visible is False
    assert view.items_content.visible is True
    view.refresh_feeds.assert_called()

    # Switch back
    view.tabs.selected_index = 0
    view.on_tab_change(None)

    assert view.feeds_content.visible is True
    assert view.items_content.visible is False


def test_rss_view_add_rss_empty():
    """Test adding empty RSS url."""
    config = {"rss_feeds": []}
    view = RSSView(config)
    view.load_feeds_list = MagicMock()

    view.rss_input.value = ""
    view.add_rss(None)

    view.load_feeds_list.assert_not_called()
    assert len(config["rss_feeds"]) == 0


def test_rss_view_fetch_task_exception():
    """Test feed fetching with one bad feed."""
    view = RSSView({"rss_feeds": ["http://good.com", "http://bad.com"]})
    view.update = MagicMock()

    # Mock page for clipboard access in item creation (though not called here)
    view.page = MagicMock()

    with patch("rss_manager.RSSManager.parse_feed") as mock_parse:

        def side_effect(url):
            if "bad" in url:
                raise Exception("Network Error")
            return [
                {"title": "Video 1", "link": "http://v1", "published": "2023-01-01"}
            ]

        mock_parse.side_effect = side_effect

        # Run directly without thread
        view._fetch_feeds_task()

        # Should have added one item
        assert len(view.items_list_view.controls) == 1
        assert (
            "Video 1"
            in view.items_list_view.controls[0].content.controls[1].controls[0].value
        )


def test_rss_view_fetch_task_empty():
    """Test fetch task with no items."""
    view = RSSView({"rss_feeds": ["http://empty.com"]})
    view.update = MagicMock()

    with patch("rss_manager.RSSManager.parse_feed", return_value=[]):
        view._fetch_feeds_task()

        assert len(view.items_list_view.controls) == 1
        assert "No recent items found" in view.items_list_view.controls[0].content.value


def test_rss_view_item_copy():
    """Test copy button on rss item."""
    view = RSSView({"rss_feeds": ["http://test.com"]})
    view.update = MagicMock()
    view.page = MagicMock()

    with patch(
        "rss_manager.RSSManager.parse_feed",
        return_value=[{"title": "T", "link": "L", "published": "D"}],
    ):
        view._fetch_feeds_task()

        # Get the item control
        container = view.items_list_view.controls[0]
        row = container.content
        copy_btn = row.controls[2]

        copy_btn.on_click(None)
        view.page.set_clipboard.assert_called_with("L")
