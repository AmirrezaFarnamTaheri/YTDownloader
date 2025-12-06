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

# from views.dashboard_view import DashboardView # Dashboard removed from nav for now?
# The AppLayout has 5 items: Download, Queue, History, RSS, Settings.
# Dashboard seems extra or replaced by RSS/History?
# Let's check AppLayout destinations. It has Icons.RSS_FEED but no Dashboard.
# Wait, AppLayout has 5 destinations: Download, Queue, History, RSS, Settings.
# The list in UIManager has 6. Index mismatch!
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

    # pylint: disable=too-many-instance-attributes
    def __init__(self, page: ft.Page):
        self.page = page
        self.download_view: Optional[DownloadView] = None
        self.queue_view: Optional[QueueView] = None
        self.history_view: Optional[HistoryView] = None
        self.rss_view: Optional[RSSView] = None
        self.settings_view: Optional[SettingsView] = None

        self.views_list: List[BaseView] = []
        self.app_layout: Optional[AppLayout] = None

        # Track current view index
        self.current_view_index = 0

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def initialize_views(
        self,
        on_fetch_info_callback,
        on_add_to_queue_callback,
        on_batch_import_callback,
        on_schedule_callback,
        on_cancel_item_callback,
        on_remove_item_callback,
        on_reorder_item_callback,
        on_retry_item_callback,
        # pylint: disable=unused-argument
        on_toggle_clipboard_callback,
        on_play_callback,  # New
        on_open_folder_callback,  # New
    ):
        """Initialize all views with their dependencies."""

        logger.debug("Initializing views...")

        self.download_view = DownloadView(
            on_fetch_info_callback,
            on_add_to_queue_callback,
            on_batch_import_callback,
            on_schedule_callback,
            state,
        )

        self.queue_view = QueueView(
            state.queue_manager,
            on_cancel_item_callback,
            on_remove_item_callback,
            on_reorder_item_callback,
            on_play_callback,
            on_open_folder_callback,
        )
        self.queue_view.on_retry = on_retry_item_callback

        self.history_view = HistoryView()
        self.rss_view = RSSView(state.config)
        self.settings_view = SettingsView(state.config)

        # Match the order in AppLayout.destinations:
        # 0: Download, 1: Queue, 2: History, 3: RSS, 4: Settings
        self.views_list = [
            self.download_view,
            self.queue_view,
            self.history_view,
            self.rss_view,
            self.settings_view,
        ]

        # AppLayout expects `on_nav_change` as the second argument
        def on_nav_change(e):
            # NavigationRail `on_change` event passes an object with `control.selected_index`
            idx = e.control.selected_index
            self.navigate_to(idx)

        self.app_layout = AppLayout(self.page, on_nav_change)
        self.app_layout.set_content(self.download_view)

        # Handle responsive layout logic if needed (AppLayout does basic rail toggle)
        # We can add listener here if we want automatic compact mode
        # But AppLayout constructor didn't have self.page attached to resize.
        # Let's just trust AppLayout logic or Page logic.

        # Restore compact mode from state
        if state.compact_mode:
            self.app_layout.toggle_compact_mode(True)

        return self.app_layout

    def navigate_to(self, index: int):
        """Navigate to the specified view index."""
        if self.app_layout and 0 <= index < len(self.views_list):
            logger.debug("Navigating to view index: %d", index)
            self.current_view_index = index
            view = self.views_list[index]
            self.app_layout.set_content(view)

            # Refresh view if needed
            if isinstance(view, HistoryView):
                view.load()
            elif isinstance(view, RSSView):
                view.load()
            elif isinstance(view, QueueView):
                view.rebuild()

            # Sync Rail index if navigated programmatically (not via click)
            self.app_layout.set_navigation_index(index)

            self.page.update()

    def update_queue_view(self):
        """Rebuild queue view if it exists."""
        if self.queue_view:
            self.queue_view.rebuild()

    def update_download_view(self):
        """Update download view state."""
        if self.download_view:
            self.download_view.update()
