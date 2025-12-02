"""
UI Manager module.

Handles view initialization, navigation, and global UI state.
"""

import logging
from typing import List, Optional

import flet as ft

from app_layout import AppLayout
from app_state import state
from views.base_view import BaseView
from views.dashboard_view import DashboardView
from views.download_view import DownloadView
from views.history_view import HistoryView
from views.queue_view import QueueView
from views.rss_view import RSSView
from views.settings_view import SettingsView

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages the application's UI, including views and layout.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.download_view: Optional[DownloadView] = None
        self.queue_view: Optional[QueueView] = None
        self.history_view: Optional[HistoryView] = None
        self.dashboard_view: Optional[DashboardView] = None
        self.rss_view: Optional[RSSView] = None
        self.settings_view: Optional[SettingsView] = None

        self.views_list: List[BaseView] = []
        self.app_layout: Optional[AppLayout] = None

        # Track current view index
        self.current_view_index = 0

    def initialize_views(self,
                         on_fetch_info_callback,
                         on_add_to_queue_callback,
                         on_batch_import_callback,
                         on_schedule_callback,
                         on_cancel_item_callback,
                         on_remove_item_callback,
                         on_reorder_item_callback,
                         on_retry_item_callback,
                         on_toggle_clipboard_callback):
        """Initialize all views with their dependencies."""

        logger.debug("Initializing views...")

        self.download_view = DownloadView(
            on_fetch_info_callback,
            on_add_to_queue_callback,
            on_batch_import_callback,
            on_schedule_callback,
            state
        )

        self.queue_view = QueueView(
            state.queue_manager,
            on_cancel_item_callback,
            on_remove_item_callback,
            on_reorder_item_callback
        )
        self.queue_view.on_retry = on_retry_item_callback

        self.history_view = HistoryView()
        self.dashboard_view = DashboardView()
        self.rss_view = RSSView(state.config)
        self.settings_view = SettingsView(state.config)

        self.views_list = [
            self.download_view,
            self.queue_view,
            self.history_view,
            self.dashboard_view,
            self.rss_view,
            self.settings_view,
        ]

        self.app_layout = AppLayout(
            self.page,
            self.navigate_to,
            on_toggle_clipboard_callback,
            state.clipboard_monitor_active,
            initial_view=self.download_view,
        )

        # Handle responsive layout
        self.page.on_resize = self._on_page_resize
        self._on_page_resize(None)

        return self.app_layout.view

    def navigate_to(self, index: int):
        """Navigate to the specified view index."""
        if 0 <= index < len(self.views_list):
            logger.debug("Navigating to view index: %d", index)
            self.current_view_index = index
            view = self.views_list[index]
            self.app_layout.set_content(view)

            # Refresh view if needed
            if isinstance(view, HistoryView):
                view.load()
            elif isinstance(view, DashboardView):
                view.load()
            elif isinstance(view, RSSView):
                view.load()

            self.page.update()

    def _on_page_resize(self, e):
        """
        Handle page resize events for responsive layout.
        Mobile breakpoints (approx): < 800px width.
        """
        is_mobile = self.page.width < 800

        if self.app_layout:
             # Use the dedicated method in AppLayout
             self.app_layout.set_sidebar_collapsed(is_mobile)

    def update_queue_view(self):
        """Rebuild queue view if it exists."""
        if self.queue_view:
            self.queue_view.rebuild()

    def update_download_view(self):
        """Update download view state."""
        if self.download_view:
            self.download_view.update()
