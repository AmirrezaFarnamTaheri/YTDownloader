import flet as ft
import logging
from theme import Theme
from .base_view import BaseView
from config_manager import ConfigManager
from rss_manager import RSSManager
import threading


logger = logging.getLogger(__name__)


class RSSView(BaseView):
    def __init__(self, config):
        super().__init__("RSS Feeds", ft.Icons.RSS_FEED)
        self.config = config
        self.rss_input = ft.TextField(
            label="Feed URL",
            hint_text="https://www.youtube.com/feeds/videos.xml?channel_id=...",
            expand=True,
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Feeds", icon=ft.Icons.LIST),
                ft.Tab(text="Latest Items", icon=ft.Icons.NEW_RELEASES),
            ],
            expand=True,
            on_change=self.on_tab_change,
        )

        self.feeds_list_view = ft.ListView(expand=True, spacing=10)
        self.items_list_view = ft.ListView(expand=True, spacing=10)

        # Tab Content
        self.feeds_content = ft.Column(
            [
                ft.Row(
                    [
                        self.rss_input,
                        ft.IconButton(
                            ft.Icons.ADD_CIRCLE,
                            on_click=self.add_rss,
                            icon_size=40,
                            icon_color=Theme.PRIMARY,
                            tooltip="Add Feed",
                        ),
                    ]
                ),
                ft.Divider(height=20, color=Theme.BORDER),
                self.feeds_list_view,
            ],
            expand=True,
        )

        self.items_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Latest Videos from your feeds",
                            size=16,
                            color=Theme.TEXT_SECONDARY,
                        ),
                        ft.IconButton(
                            ft.Icons.REFRESH,
                            on_click=self.refresh_feeds,
                            icon_color=Theme.PRIMARY,
                            tooltip="Refresh",
                        ),
                    ]
                ),
                ft.Divider(height=10, color=Theme.BORDER),
                self.items_list_view,
            ],
            expand=True,
            visible=False,
        )

        self.add_control(self.tabs)
        self.add_control(self.feeds_content)
        self.add_control(self.items_content)

    def on_tab_change(self, e):
        if self.tabs.selected_index == 0:
            self.feeds_content.visible = True
            self.items_content.visible = False
        else:
            self.feeds_content.visible = False
            self.items_content.visible = True
            self.refresh_feeds(None)
        self.update()

    def load(self):
        self.load_feeds_list()
        self.update()

    def load_feeds_list(self):
        self.feeds_list_view.controls.clear()
        feeds = self.config.get("rss_feeds", [])

        if not feeds:
            self.feeds_list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RSS_FEED, size=64, color=Theme.TEXT_MUTED),
                            ft.Text("No feeds added yet", color=Theme.TEXT_MUTED),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )

        for feed in feeds:
            self.feeds_list_view.controls.append(
                ft.Container(
                    padding=10,
                    bgcolor=Theme.BG_CARD,
                    border_radius=8,
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.RSS_FEED, color=Theme.WARNING),
                            ft.Text(
                                feed,
                                color=Theme.TEXT_PRIMARY,
                                expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                on_click=lambda e, f=feed: self.remove_rss(f),
                                icon_color=Theme.ERROR,
                                tooltip="Remove",
                            ),
                        ]
                    ),
                )
            )

    def add_rss(self, e):
        if not self.rss_input.value:
            return
        feeds = self.config.get("rss_feeds", [])
        if self.rss_input.value not in feeds:
            feeds.append(self.rss_input.value)
            self.config["rss_feeds"] = feeds
            ConfigManager.save_config(self.config)
            self.load_feeds_list()
            self.rss_input.value = ""
            self.update()

    def remove_rss(self, feed):
        feeds = self.config.get("rss_feeds", [])
        if feed in feeds:
            feeds.remove(feed)
            self.config["rss_feeds"] = feeds
            ConfigManager.save_config(self.config)
            self.load_feeds_list()
            self.update()

    def refresh_feeds(self, e):
        self.items_list_view.controls.clear()
        self.items_list_view.controls.append(
            ft.ProgressBar(width=None, color=Theme.PRIMARY)
        )
        self.update()

        threading.Thread(target=self._fetch_feeds_task, daemon=True).start()

    def _fetch_feeds_task(self):
        feeds = self.config.get("rss_feeds", [])
        all_items = []
        failed_feeds = []

        for url in feeds:
            try:
                items = RSSManager.parse_feed(url)
                # Limit to top 3 per feed to avoid spam
                all_items.extend(items[:3])
            except Exception as exc:
                logger.warning("Failed to fetch RSS feed %s: %s", url, exc)
                failed_feeds.append(url)

        # Sort by date desc (basic string sort for ISO format often works, but proper parsing is better)
        # RSSManager returns 'published' as string.
        all_items.sort(key=lambda x: x.get("published", ""), reverse=True)

        self.items_list_view.controls.clear()

        if not all_items:
            self.items_list_view.controls.append(
                ft.Container(
                    content=ft.Text("No recent items found", color=Theme.TEXT_MUTED),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )

        if failed_feeds and not all_items:
            self.items_list_view.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"Failed to load {len(failed_feeds)} feed(s). Check URLs and network.",
                        color=Theme.WARNING,
                    ),
                    padding=8,
                )
            )

        for item in all_items:
            self.items_list_view.controls.append(
                ft.Container(
                    padding=10,
                    bgcolor=Theme.BG_CARD,
                    border_radius=8,
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.VIDEO_LIBRARY, color=Theme.ACCENT),
                            ft.Column(
                                [
                                    ft.Text(
                                        item["title"],
                                        weight=ft.FontWeight.BOLD,
                                        color=Theme.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        f"{item.get('published', '')} • {item.get('link', '')}",
                                        size=12,
                                        color=Theme.TEXT_SECONDARY,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                                expand=True,
                            ),
                            ft.IconButton(
                                ft.Icons.COPY,
                                icon_color=Theme.TEXT_SECONDARY,
                                tooltip="Copy Link",
                                on_click=lambda e, l=item[
                                    "link"
                                ]: self.page.set_clipboard(l),
                            ),
                        ]
                    ),
                )
            )

        self.update()
