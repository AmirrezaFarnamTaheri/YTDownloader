"""
App Layout module.

Defines the main application layout including the sidebar navigation,
bottom navigation (for mobile), and content area management.
Refactored for full responsiveness.
"""

import logging
from typing import List, Optional

import flet as ft

from theme import Theme

logger = logging.getLogger(__name__)


class AppLayout:
    """
    Main application layout component.
    Handles responsive switching between Sidebar (Desktop) and NavigationBar (Mobile).
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        page: ft.Page,
        navigate_callback,
        toggle_clipboard_callback,
        clipboard_active: bool = False,
        initial_view: Optional[ft.Control] = None,
    ):
        self.page = page
        self.navigate_callback = navigate_callback
        self.toggle_clipboard_callback = toggle_clipboard_callback
        self._current_index = 0

        # Define Navigation Items
        self.nav_items = [
            ("Download", ft.Icons.DOWNLOAD_OUTLINED, ft.Icons.DOWNLOAD),
            ("Queue", ft.Icons.QUEUE_MUSIC_OUTLINED, ft.Icons.QUEUE_MUSIC),
            ("History", ft.Icons.HISTORY_OUTLINED, ft.Icons.HISTORY),
            ("Dashboard", ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD),
            ("RSS Feeds", ft.Icons.RSS_FEED_OUTLINED, ft.Icons.RSS_FEED),
            ("Settings", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS),
        ]

        # --- Components ---

        # 1. Main Content Area
        self.content_area = ft.Container(
            content=initial_view,
            expand=True,
            padding=ft.padding.all(10),  # Default smaller padding, adjusted dynamically
        )

        # 2. Navigation Rail (Desktop)
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=icon_outlined,
                    selected_icon=icon_filled,
                    label=label,
                )
                for label, icon_outlined, icon_filled in self.nav_items
            ],
            on_change=self._on_nav_change,
            bgcolor=Theme.Surface.BG,
            extended=True,
        )

        # 3. Navigation Bar (Mobile)
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(
                    icon=icon_outlined,
                    selected_icon=icon_filled,
                    label=label,
                )
                for label, icon_outlined, icon_filled in self.nav_items
            ],
            on_change=self._on_nav_change,
            visible=False,  # Hidden by default
            bgcolor=Theme.Surface.BG,
            height=70,
        )

        # Attach Nav Bar to Page
        self.page.navigation_bar = self.nav_bar

        # 4. Sidebar Container (Holds Rail + Logo + Switch)
        self.clipboard_switch = ft.Switch(
            label="Clipboard Monitor",
            value=clipboard_active,
            on_change=self._on_clipboard_toggle,
        )

        self.logo_image = ft.Image(
            src="assets/logo.svg",
            width=48,
            height=48,
            color=Theme.Primary.MAIN,
        )
        self.logo_text = ft.Text(
            "StreamCatch",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=Theme.Text.PRIMARY,
        )

        self.header = ft.Container(
            content=ft.Column(
                [self.logo_image, self.logo_text],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            padding=ft.padding.only(top=20, bottom=10),
        )

        self.sidebar = ft.Container(
            content=ft.Column(
                [
                    self.header,
                    ft.Divider(color=Theme.Divider.COLOR, thickness=1),
                    ft.Container(content=self.rail, expand=True),
                    ft.Divider(color=Theme.Divider.COLOR, thickness=1),
                    ft.Container(
                        content=self.clipboard_switch, padding=ft.padding.all(15)
                    ),
                ],
                spacing=0,
            ),
            width=200,
            bgcolor=Theme.Surface.BG,
            border=ft.border.only(right=ft.BorderSide(1, Theme.Divider.COLOR)),
            visible=True,  # Visible by default (Desktop)
        )

        # 5. Root View
        self.view = ft.Row(
            [
                self.sidebar,
                self.content_area,
            ],
            expand=True,
            spacing=0,
        )

        # Setup Resize Handler
        self.page.on_resized = self._on_resized
        # Trigger initial check
        self._on_resized(None)

    def set_sidebar_collapsed(self, collapsed: bool):
        """External method to force sidebar/navbar state (e.g. from UIManager)."""
        is_mobile = collapsed

        if is_mobile:
            if self.sidebar.visible:
                self.sidebar.visible = False
                self.nav_bar.visible = True
                self.content_area.padding = 10
                self.view.update()
                self.page.update()
        else:
            if not self.sidebar.visible:
                self.sidebar.visible = True
                self.nav_bar.visible = False
                self.content_area.padding = 20
                self.view.update()
                self.page.update()

    def _on_resized(self, e):
        """Handle screen resize events to switch layouts."""
        width = self.page.width
        # Mobile threshold
        is_mobile = width < 800
        self.set_sidebar_collapsed(is_mobile)

    def set_compact_mode(self, enabled: bool):
        """Enable or disable Compact Mode (Desktop specific)."""
        # Only relevant if sidebar is visible
        if not self.sidebar.visible:
            return

        if enabled:
            self.rail.extended = False
            self.rail.min_width = 70
            self.rail.label_type = ft.NavigationRailLabelType.NONE
            self.sidebar.width = 70
            self.logo_text.visible = False
            self.clipboard_switch.label = ""
            self.clipboard_switch.tooltip = "Clipboard Monitor"
        else:
            self.rail.extended = True
            self.rail.min_width = 100
            self.rail.label_type = ft.NavigationRailLabelType.ALL
            self.sidebar.width = 200
            self.logo_text.visible = True
            self.clipboard_switch.label = "Clipboard Monitor"
            self.clipboard_switch.tooltip = None

        self.view.update()

    def _on_nav_change(self, e):
        """Handle navigation changes from either Rail or Bar."""
        index = e.control.selected_index
        self._current_index = index

        # Sync both controls
        self.rail.selected_index = index
        self.nav_bar.selected_index = index

        logger.info("Navigation changed to index: %d", index)
        self.navigate_callback(index)

        # Update UI to reflect sync
        if self.sidebar.visible:
            self.rail.update()
        if self.nav_bar.visible:
            self.nav_bar.update()

    def _on_clipboard_toggle(self, e):
        logger.info("Clipboard monitor toggled to: %s", e.control.value)
        self.toggle_clipboard_callback(e.control.value)

    def set_content(self, view_control):
        """Update the main content area with a new view."""
        logger.debug("Setting content view: %s", type(view_control).__name__)
        self.content_area.content = view_control
        try:
            self.content_area.update()
        except AssertionError:
            pass
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to update content area: %s", e)
