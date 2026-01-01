"""
AppLayout module.
Manages the main layout structure (Sidebar vs. Content) and responsive behavior.
Refactored to support Compact Mode and better responsiveness.
"""

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme


# pylint: disable=too-many-instance-attributes
class AppLayout(ft.Row):
    """
    Main application layout using a Row of [Sidebar, Content].
    Supports responsiveness via checking page width.
    """

    def __init__(self, page: ft.Page, on_nav_change):
        super().__init__()
        self.page = page
        self.on_nav_change = on_nav_change
        self.expand = True
        self.spacing = 0

        # Define Navigation Destinations
        self.destinations = [
            ft.NavigationRailDestination(
                icon=ft.icons.DASHBOARD_OUTLINED,
                selected_icon=ft.icons.DASHBOARD_ROUNDED,
                label=LM.get("dashboard", "Dashboard"),
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.DOWNLOAD_OUTLINED,
                selected_icon=ft.icons.DOWNLOAD_ROUNDED,
                label=LM.get("download"),
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.LIST_ALT_OUTLINED,
                selected_icon=ft.icons.LIST_ALT_ROUNDED,
                label=LM.get("queue"),
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.HISTORY_TOGGLE_OFF_OUTLINED,
                selected_icon=ft.icons.HISTORY_ROUNDED,
                label=LM.get("history"),
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.RSS_FEED_OUTLINED,
                selected_icon=ft.icons.RSS_FEED_ROUNDED,
                label=LM.get("rss"),
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.SETTINGS_OUTLINED,
                selected_icon=ft.icons.SETTINGS_ROUNDED,
                label=LM.get("settings"),
            ),
        ]

        # Navigation Rail (Sidebar)
        self.rail = ft.NavigationRail(
            selected_index=0,  # type: ignore
            label_type=ft.NavigationRailLabelType.ALL,
            on_change=self.on_nav_change,
            destinations=self.destinations,
            bgcolor=Theme.BG_LIGHT,
            indicator_color=Theme.Primary.MAIN,
            extended=True,
            min_width=72,
            min_extended_width=200,
            group_alignment=-0.9,
        )

        # Bottom Navigation Bar (Mobile) - Hidden by default
        self.bottom_nav = ft.NavigationBar(
            selected_index=0,
            on_change=self.on_nav_change,
            destinations=self.destinations,
            visible=False
        )

        # Content Area
        self.content_area = ft.Container(
            expand=True,
            bgcolor=Theme.BG_DARK,
            padding=20,  # Consistent padding
            content=ft.Column(),  # Placeholder
        )

        # Use Container for sidebar to allow finer control if needed
        self.sidebar_container = ft.Container(
            content=self.rail,
            width=200,  # Initial width
            bgcolor=Theme.BG_LIGHT,
        )

        # Vertical Divider
        self.v_divider = ft.Container(width=1, bgcolor=Theme.DIVIDER)

        self.controls = [
            self.sidebar_container,
            self.v_divider,
            self.content_area,
        ]

    def set_content(self, view_control: ft.Control):
        """Updates the main content area."""
        self.content_area.content = view_control
        self.content_area.update()

    def toggle_compact_mode(self, is_compact: bool):
        """Toggles sidebar compact mode."""
        self.rail.extended = not is_compact
        self.sidebar_container.width = 72 if is_compact else 200
        self.rail.label_type = (
            ft.NavigationRailLabelType.NONE
            if is_compact
            else ft.NavigationRailLabelType.ALL
        )
        self.sidebar_container.update()
        self.rail.update()

    def toggle_mobile_mode(self, is_mobile: bool):
        """Toggles between Sidebar and Bottom Navigation."""
        if is_mobile:
            self.sidebar_container.visible = False
            self.v_divider.visible = False
            # Bottom nav is usually attached to Page.navigation_bar
            # But we can also insert it if page structure allows.
            # Best practice in Flet: assign to page.navigation_bar
            self.page.navigation_bar = self.bottom_nav
            self.bottom_nav.visible = True
            self.page.update()
        else:
            self.sidebar_container.visible = True
            self.v_divider.visible = True
            self.page.navigation_bar = None
            self.bottom_nav.visible = False
            self.page.update()

        self.sidebar_container.update()
        self.v_divider.update()

    def handle_resize(self, width: float, height: float):
        """
        Adjust layout based on window size.
        Breakpoints:
        - < 600px: Bottom Nav (Mobile)
        - 600-1200px: Compact Rail
        - > 1200px: Extended Rail
        """
        # pylint: disable=unused-argument
        if width < 600:
            if self.sidebar_container.visible:
                self.toggle_mobile_mode(True)
        elif width < 1200:
            # Tablet/Small Laptop: Compact Rail
            if not self.sidebar_container.visible:
                self.toggle_mobile_mode(False)

            if self.rail.extended:
                self.toggle_compact_mode(True)
        else:
            # Desktop: Extended Rail
            if not self.sidebar_container.visible:
                self.toggle_mobile_mode(False)

            if not self.rail.extended:
                self.toggle_compact_mode(False)

    def set_navigation_index(self, index: int):
        """Sets the selected navigation index programmatically."""
        self.rail.selected_index = index  # type: ignore
        self.rail.update()
        if self.bottom_nav.visible:
             self.bottom_nav.selected_index = index
             self.bottom_nav.update()
