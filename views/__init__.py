"""Views package for StreamCatch application."""

from views.base_view import BaseView
from views.download_view import DownloadView
from views.history_view import HistoryView
from views.queue_view import QueueView
from views.rss_view import RSSView
from views.settings_view import SettingsView

__all__ = [
    "DownloadView",
    "QueueView",
    "HistoryView",
    "SettingsView",
    "RSSView",
    "BaseView",
]
