import flet as ft
from theme import Theme
from .base_view import BaseView
from config_manager import ConfigManager

class RSSView(BaseView):
    def __init__(self, config):
        super().__init__("RSS Feeds", ft.Icons.RSS_FEED)
        self.config = config
        self.rss_input = ft.TextField(label="Feed URL", expand=True, border_color=Theme.BORDER, border_radius=8, bgcolor=Theme.BG_CARD)
        self.rss_list_view = ft.ListView(expand=True)

        self.add_control(
            ft.Row([
                self.rss_input,
                ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=self.add_rss, icon_size=40, icon_color=Theme.PRIMARY)
            ])
        )
        self.add_control(self.rss_list_view)

    def load(self):
        self.rss_list_view.controls.clear()
        for feed in self.config.get('rss_feeds', []):
            self.rss_list_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.RSS_FEED, color=Theme.WARNING),
                    title=ft.Text(feed, color=Theme.TEXT_PRIMARY),
                    trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda e, f=feed: self.remove_rss(f), icon_color=Theme.TEXT_SECONDARY)
                )
            )
        self.update()

    def add_rss(self, e):
        if not self.rss_input.value: return
        feeds = self.config.get('rss_feeds', [])
        if self.rss_input.value not in feeds:
            feeds.append(self.rss_input.value)
            self.config['rss_feeds'] = feeds
            ConfigManager.save_config(self.config)
            self.load()
            self.rss_input.value = ""
            self.update()

    def remove_rss(self, feed):
        feeds = self.config.get('rss_feeds', [])
        if feed in feeds:
            feeds.remove(feed)
            self.config['rss_feeds'] = feeds
            ConfigManager.save_config(self.config)
            self.load()
