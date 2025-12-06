"""
RSS View Module.

Displays a list of RSS feeds and their latest items.
Allows adding and removing feeds.
"""

import logging
import threading

import flet as ft

from config_manager import ConfigManager
from localization_manager import LocalizationManager as LM
from rss_manager import RSSManager
from views.base_view import BaseView

logger = logging.getLogger(__name__)


class RSSView(BaseView):
    """View for managing and viewing RSS feeds."""

    def __init__(self, config):
        super().__init__(LM.get("rss"), ft.Icons.RSS_FEED)
        self.config = config
        self.rss_manager = RSSManager(config)
        self.feed_list = ft.ListView(expand=True, spacing=10, padding=20)
        self.items_list = ft.ListView(expand=True, spacing=10, padding=20)
        self.rss_input = ft.TextField(
            label=LM.get("rss_feed_url"), expand=True, on_submit=self.add_rss
        )

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text=LM.get("feeds"),
                    icon=ft.Icons.RSS_FEED,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    self.rss_input,
                                    ft.IconButton(
                                        icon=ft.Icons.ADD,
                                        tooltip=LM.get("add_feed"),
                                        on_click=self.add_rss,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.REFRESH,
                                        on_click=self.refresh_feeds,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Divider(),
                            self.feed_list,
                        ],
                        expand=True,
                    ),
                ),
                ft.Tab(
                    text=LM.get("latest_items"),
                    icon=ft.Icons.NEW_RELEASES,
                    content=self.items_list,
                ),
            ],
            expand=True,
            on_change=self.on_tab_change,
        )

        self.controls = [self.tabs]

    def load(self):
        """Load data when view is shown."""
        self.load_feeds_list()

    def load_feeds_list(self):
        """Render the list of subscribed feeds."""
        self.feed_list.controls.clear()
        feeds = self.config.get("rss_feeds", [])

        # Normalize feeds
        normalized_feeds = []
        for f in feeds:
            if isinstance(f, str):
                normalized_feeds.append({"url": f, "name": f})
            else:
                normalized_feeds.append(f)

        if not normalized_feeds:
            self.feed_list.controls.append(ft.Text(LM.get("no_rss_feeds"), italic=True))
        else:
            for feed in normalized_feeds:
                url = feed.get("url")
                name = feed.get("name", url)

                self.feed_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.RSS_FEED),
                                    ft.Column(
                                        [
                                            ft.Text(name, weight=ft.FontWeight.BOLD),
                                            ft.Text(
                                                url,
                                                size=12,
                                                color=ft.Colors.GREY,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                        ],
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED,
                                        on_click=lambda e, f=feed: self.remove_rss(f),
                                    ),
                                ]
                            ),
                            padding=10,
                        )
                    )
                )
        self.update()

    # pylint: disable=unused-argument
    def add_rss(self, e):
        """Add a new RSS feed."""
        new_url = self.rss_input.value
        if not new_url:
            return

        feeds = self.config.get("rss_feeds", [])

        exists = False
        for f in feeds:
            f_url = f if isinstance(f, str) else f.get("url")
            if f_url == new_url:
                exists = True
                break

        if not exists:
            feeds.append({"url": new_url, "name": new_url})
            self.config["rss_feeds"] = feeds
            ConfigManager.save_config(self.config)
            self.load_feeds_list()
            self.rss_input.value = ""
            self.update()

    def remove_rss(self, feed):
        """Remove an RSS feed."""
        feeds = self.config.get("rss_feeds", [])
        target_url = feed.get("url") if isinstance(feed, dict) else feed
        new_feeds = [
            f
            for f in feeds
            if (f if isinstance(f, str) else f.get("url")) != target_url
        ]

        if len(new_feeds) != len(feeds):
            self.config["rss_feeds"] = new_feeds
            ConfigManager.save_config(self.config)
            self.load_feeds_list()
            self.update()

    # pylint: disable=unused-argument

    def refresh_feeds(self, e):
        """Fetch latest items from all feeds."""
        self.items_list.controls.clear()
        self.items_list.controls.append(ft.ProgressBar())
        self.update()
        threading.Thread(target=self._fetch_feeds_task, daemon=True).start()

    def _fetch_feeds_task(self):
        """Task to fetch feeds."""
        items = self.rss_manager.get_all_items()
        self.items_list.controls.clear()
        if not items:
            self.items_list.controls.append(ft.Text(LM.get("no_items_found")))
        else:
            for item in items:
                self.items_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(item["title"], weight=ft.FontWeight.BOLD),
                                    ft.Text(
                                        f"{item['feed_name']} - {item['published']}",
                                        size=12,
                                        color=ft.Colors.GREY,
                                    ),
                                    ft.Row(
                                        [
                                            ft.ElevatedButton(
                                                "Open",
                                                on_click=lambda e, url=item[
                                                    "link"
                                                ]: self.page.launch_url(url),
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                            padding=10,
                        )
                    )
                )
        self.update()
        # Also refresh list names in case they updated
        # pylint: disable=unused-argument
        self.load_feeds_list()

    def on_tab_change(self, e):
        """Handle tab change."""
        if self.tabs.selected_index == 1:
            # Auto refresh if empty?
            if not self.items_list.controls:
                self.refresh_feeds(None)
