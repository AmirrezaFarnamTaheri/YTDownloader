"""
RSS View Module.

Displays a list of RSS feeds and their latest items.
Allows adding and removing feeds.
"""

import logging
import threading

import flet as ft

from localization_manager import LocalizationManager as LM
from rss_manager import RSSManager
from theme import Theme
from ui_utils import validate_url
from views.base_view import BaseView

logger = logging.getLogger(__name__)


class RSSView(BaseView):
    """View for managing and viewing RSS feeds."""

    def __init__(self, config):
        super().__init__(LM.get("rss"), ft.icons.RSS_FEED)
        self.config = config
        self.rss_manager = RSSManager(config)
        self.feed_list = ft.ListView(expand=True, spacing=10, padding=10)
        self.items_list = ft.ListView(expand=True, spacing=10, padding=10)

        self.rss_input = ft.TextField(
            label=LM.get("rss_feed_url"),
            expand=True,
            on_submit=self.add_rss,
            **Theme.get_input_decoration(prefix_icon=ft.icons.RSS_FEED),
        )

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            indicator_color=Theme.Primary.MAIN,
            label_color=Theme.Primary.MAIN,
            unselected_label_color=Theme.Text.SECONDARY,
            tabs=[
                ft.Tab(
                    text=LM.get("feeds"),
                    icon=ft.icons.RSS_FEED,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        self.rss_input,
                                        ft.IconButton(
                                            icon=ft.icons.ADD_CIRCLE,
                                            tooltip=LM.get("add_feed"),
                                            icon_color=Theme.Status.SUCCESS,
                                            on_click=self.add_rss,
                                            icon_size=32,
                                        ),
                                        ft.IconButton(
                                            icon=ft.icons.REFRESH,
                                            tooltip=LM.get("refresh_feeds", "Refresh"),
                                            icon_color=Theme.Text.SECONDARY,
                                            on_click=self.refresh_feeds,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Divider(color=Theme.DIVIDER),
                                self.feed_list,
                            ],
                            expand=True,
                            spacing=15,
                        ),
                        padding=10,
                    ),
                ),
                ft.Tab(
                    text=LM.get("latest_items"),
                    icon=ft.icons.NEW_RELEASES,
                    content=ft.Container(content=self.items_list, padding=10),
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
        normalized_feeds = self.rss_manager.get_feeds()

        if not normalized_feeds:
            self.feed_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        LM.get("no_rss_feeds"), italic=True, color=Theme.TEXT_MUTED
                    ),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )
        else:
            for feed in normalized_feeds:
                url = feed.get("url")
                name = feed.get("name", url)

                # Feed Item Card
                card_style = Theme.get_card_decoration()
                self.feed_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.icons.RSS_FEED, color=Theme.Primary.MAIN),
                                ft.Column(
                                    [
                                        ft.Text(
                                            name,
                                            weight=ft.FontWeight.BOLD,
                                            color=Theme.Text.PRIMARY,
                                        ),
                                        ft.Text(
                                            url,
                                            size=12,
                                            color=Theme.Text.SECONDARY,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE_OUTLINE,
                                    tooltip=LM.get("remove_feed", "Remove Feed"),
                                    icon_color=Theme.Status.ERROR,
                                    on_click=lambda e, f=feed: self.remove_rss(f),
                                ),
                            ]
                        ),
                        **card_style,
                    )
                )
        self.update()

    # pylint: disable=unused-argument
    def add_rss(self, e):
        """Add a new RSS feed."""
        new_url = self.rss_input.value
        if not new_url:
            return

        if not validate_url(new_url):
            if self.page:
                self.page.open(ft.SnackBar(content=ft.Text(LM.get("invalid_url"))))
            self.rss_input.error_text = LM.get("invalid_url")
            self.rss_input.update()
            return

        self.rss_manager.add_feed(new_url)
        self.load_feeds_list()
        self.rss_input.value = ""
        self.rss_input.error_text = None
        self.update()

    def remove_rss(self, feed):
        """Remove an RSS feed."""
        target_url = feed.get("url") if isinstance(feed, dict) else feed
        self.rss_manager.remove_feed(target_url)
        self.load_feeds_list()
        self.update()

    # pylint: disable=unused-argument

    def refresh_feeds(self, e):
        """Fetch latest items from all feeds."""
        self.items_list.controls.clear()
        self.items_list.controls.append(ft.ProgressBar(color=Theme.Primary.MAIN))
        self.update()
        threading.Thread(target=self._fetch_feeds_task, daemon=True).start()

    def _fetch_feeds_task(self):
        """Task to fetch feeds."""
        items = self.rss_manager.get_all_items()

        def apply_updates():
            self.items_list.controls.clear()
            if not items:
                self.items_list.controls.append(
                    ft.Text(LM.get("no_items_found"), color=Theme.TEXT_MUTED)
                )
            else:
                for item in items:
                    # News Item Card - use .get() to prevent KeyError
                    card_style = Theme.get_card_decoration()
                    title = item.get("title", LM.get("unknown_title"))
                    feed_name = item.get("feed_name", "")
                    published = item.get("published", "")
                    link = item.get("link", "")

                    self.items_list.controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        title,
                                        weight=ft.FontWeight.BOLD,
                                        color=Theme.Text.PRIMARY,
                                    ),
                                    ft.Text(
                                        f"{feed_name} - {published}",
                                        size=12,
                                        color=Theme.Text.SECONDARY,
                                    ),
                                    ft.Row(
                                        [
                                            ft.ElevatedButton(
                                                LM.get("open"),
                                                icon=ft.icons.OPEN_IN_NEW,
                                                style=ft.ButtonStyle(
                                                    bgcolor=Theme.Surface.BG,
                                                    color=Theme.Primary.MAIN,
                                                ),
                                                on_click=lambda e, url=link: (
                                                    self.page.launch_url(url)
                                                    if self.page and url
                                                    else None
                                                ),
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.END,
                                    ),
                                ]
                            ),
                            **card_style,
                        )
                    )
            self.update()
            # Also refresh list names in case they updated
            self.load_feeds_list()

        if self.page and hasattr(self.page, "run_task"):
            self.page.run_task(apply_updates)
        else:
            apply_updates()

    def on_tab_change(self, e):
        """Handle tab change."""
        if self.tabs.selected_index == 1:
            # Auto refresh if empty?
            if not self.items_list.controls:
                self.refresh_feeds(None)
