"""Views package for StreamCatch application."""

from views.download_view import DownloadView
from views.queue_view import QueueView
from views.history_view import HistoryView
from views.settings_view import SettingsView
from views.dashboard_view import DashboardView
from views.rss_view import RSSView
from views.base_view import BaseView

__all__ = [
    "DownloadView",
    "QueueView",
    "HistoryView",
    "SettingsView",
    "DashboardView",
    "RSSView",
    "BaseView",
]
