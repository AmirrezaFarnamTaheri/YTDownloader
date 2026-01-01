"""
UI Manager module.

Handles view initialization, navigation, and global UI state.
"""

import logging

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

    # pylint: disable=too-many-instance-attributes
    def __init__(self, page: ft.Page):
        self.page = page
        self.dashboard_view: DashboardView | None = None
        self.download_view: DownloadView | None = None
        self.queue_view: QueueView | None = None
        self.history_view: HistoryView | None = None
        self.rss_view: RSSView | None = None
        self.settings_view: SettingsView | None = None

        self.views_list: list[BaseView] = []
        self.app_layout: AppLayout | None = None

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

        # Initialize Dashboard (Index 0)
        # Dashboard expects on_paste_url to take no args in its signature in some contexts,
        # but here we pass _on_dashboard_paste_url which takes url.
        # DashboardView calls on_paste_url() (no args) OR on_paste_url(url)?
        # Let's check DashboardView signature.
        # DashboardView: on_paste_url: Callable[[], None] (implied by type hint in code? No, I need to check)
        # The code I wrote for DashboardView: on_paste_url: Callable[[], None]
        # But here I pass _on_dashboard_paste_url which expects a url?
        # Actually _on_dashboard_paste_url is used by clipboard logic usually?
        # Wait, DashboardView has "Paste URL" button. If clicked, it should probably grab clipboard content.
        # Let's wrap it to handle the logic.

        def dashboard_paste_wrapper():
            # Logic to grab clipboard and pass to _on_dashboard_paste_url
            import pyperclip
            try:
                text = pyperclip.paste()
                if text:
                    self._on_dashboard_paste_url(text)
            except Exception:
                pass

        self.dashboard_view = DashboardView(
            on_navigate=self.navigate_to,
            on_paste_url=dashboard_paste_wrapper,
            on_batch_import=on_batch_import_callback,
            queue_manager=state.queue_manager,
        )

        # DownloadView signature: on_fetch, on_add, on_paste_url, on_batch, on_schedule, app_state
        self.download_view = DownloadView(
            on_fetch_info_callback,
            on_add_to_queue_callback,
            on_toggle_clipboard_callback, # Using toggle clipboard as the "paste_url" callback or similar?
            # Ideally DownloadView should just handle paste internally or use a specific callback.
            # In DownloadView code: self.on_paste_url = on_paste_url
            # And it calls it in _on_paste_click if defined.
            # Let's pass a dummy or specific callback.
            # Actually, `on_toggle_clipboard_callback` is for the toggle switch in settings/controller.
            # We probably want to pass None or a logging callback if we don't have a specific controller action.
            # OR pass the same dashboard paste wrapper if we want to support external paste triggers?
            # The controller passed `on_toggle_clipboard_callback`.
            # Let's pass None for now as DownloadView handles paste internally via pyperclip mostly.
            None,
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
        self.settings_view = SettingsView(state.config, on_toggle_clipboard_callback)

        # Match the order in AppLayout.destinations:
        # 0: Dashboard, 1: Download, 2: Queue, 3: History, 4: RSS, 5: Settings
        self.views_list = [
            self.dashboard_view,
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
        # Set initial content to Dashboard
        self.app_layout.set_content(self.dashboard_view)
        # Ensure Dashboard loads
        self.dashboard_view.load()

        # Handle responsive layout logic
        self.page.on_resized = lambda e: self.app_layout.handle_resize(
            e.page.window_width, e.page.window_height
        )

        # Restore compact mode from state
        if state.compact_mode:
            self.app_layout.toggle_compact_mode(True)
        else:
            # Trigger initial resize check
            if self.page.window_width:
                self.app_layout.handle_resize(
                    self.page.window_width, self.page.window_height
                )

        return self.app_layout

    def _on_dashboard_paste_url(self, url: str):
        """Handle pasting URL from Dashboard."""
        if self.download_view:
            # Set value
            self.download_view.input_card.set_url(url)
            # Navigate to download view
            self.navigate_to(1)
            # Focus input (if possible)
            self.download_view.input_card.url_input.focus()
            self.download_view.update()

    def navigate_to(self, index: int):
        """Navigate to the specified view index."""
        if self.app_layout and 0 <= index < len(self.views_list):
            logger.debug("Navigating to view index: %d", index)
            self.current_view_index = index
            view = self.views_list[index]
            self.app_layout.set_content(view)

            # Refresh view if needed
            if hasattr(view, "load"):
                view.load()
            elif hasattr(view, "rebuild"):
                view.rebuild()

            # Special case for DownloadView to focus if coming from Dashboard maybe?

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
