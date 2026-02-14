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

    def __init__(self, page: ft.Page, on_nav_change, compact_mode: bool = False):
        super().__init__()
        self.page = page
        self.on_nav_change = on_nav_change
        self.expand = True
        self.spacing = 0
        self.forced_compact_mode = compact_mode

        # Define Navigation Data
        nav_data = [
            (
                ft.icons.DASHBOARD_OUTLINED,
                ft.icons.DASHBOARD_ROUNDED,
                "dashboard",
                "Dashboard",
            ),
            (ft.icons.DOWNLOAD_OUTLINED, ft.icons.DOWNLOAD_ROUNDED, "download", None),
            (ft.icons.LIST_ALT_OUTLINED, ft.icons.LIST_ALT_ROUNDED, "queue", None),
            (
                ft.icons.HISTORY_TOGGLE_OFF_OUTLINED,
                ft.icons.HISTORY_ROUNDED,
                "history",
                None,
            ),
            (ft.icons.RSS_FEED_OUTLINED, ft.icons.RSS_FEED_ROUNDED, "rss", None),
            (ft.icons.SETTINGS_OUTLINED, ft.icons.SETTINGS_ROUNDED, "settings", None),
        ]

        self.rail_destinations = [
            ft.NavigationRailDestination(
                icon=icon,
                selected_icon=selected,
                label=LM.get(key, default) if default else LM.get(key),
            )
            for icon, selected, key, default in nav_data
        ]

        self.bottom_destinations = [
            ft.NavigationDestination(
                icon=icon,
                selected_icon=selected,
                label=LM.get(key, default) if default else LM.get(key),
            )
            for icon, selected, key, default in nav_data
        ]

        # Navigation Rail (Sidebar)
        self.rail = ft.NavigationRail(
            selected_index=0,  # type: ignore
            label_type=ft.NavigationRailLabelType.ALL,
            on_change=self.on_nav_change,
            destinations=self.rail_destinations,
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
            destinations=self.bottom_destinations,
            visible=False,
            bgcolor=Theme.BG_LIGHT,
        )

        # Content Area
        self.content_area = ft.Container(
            expand=True,
            bgcolor=Theme.BG_DARK,
            gradient=Theme.get_surface_gradient(),
            padding=20,  # Initial padding
            content=ft.Column(),  # Placeholder
        )

        # Use Container for sidebar to allow finer control if needed
        self.sidebar_container = ft.Container(
            content=self.rail,
            width=200,  # Initial width
            bgcolor=Theme.BG_LIGHT,
            gradient=Theme.get_sidebar_gradient(),
        )

        # Vertical Divider
        self.v_divider = ft.Container(width=1, bgcolor=Theme.DIVIDER)

        self.controls = [
            self.sidebar_container,
            self.v_divider,
            self.content_area,
        ]

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        """Update a control only when it has been attached to a page."""
        try:
            control.update()
        except Exception as ex:  # pylint: disable=broad-exception-caught
            if "Control must be added to the page first" in str(ex):
                return
            raise

    def set_content(self, view_control: ft.Control):
        """Updates the main content area."""
        self.content_area.content = view_control
        self._safe_update(self.content_area)

    def toggle_compact_mode(self, is_compact: bool):
        """Toggles sidebar compact mode and adjusts padding."""
        self.rail.extended = not is_compact
        self.sidebar_container.width = 72 if is_compact else 200
        self.rail.label_type = (
            ft.NavigationRailLabelType.NONE
            if is_compact
            else ft.NavigationRailLabelType.ALL
        )

        # Adjust padding
        self.content_area.padding = 10 if is_compact else 20

        self._safe_update(self.sidebar_container)
        self._safe_update(self.rail)
        self._safe_update(self.content_area)

    def toggle_mobile_mode(self, is_mobile: bool):
        """Toggles between Sidebar and Bottom Navigation."""
        if is_mobile:
            self.sidebar_container.visible = False
            self.v_divider.visible = False
            # Bottom nav is usually attached to Page.navigation_bar
            # Best practice in Flet: assign to page.navigation_bar
            self.page.navigation_bar = self.bottom_nav
            self.bottom_nav.visible = True
            self._safe_update(self.page)
        else:
            self.sidebar_container.visible = True
            self.v_divider.visible = True
            self.page.navigation_bar = None
            self.bottom_nav.visible = False
            self._safe_update(self.page)

        self._safe_update(self.sidebar_container)
        self._safe_update(self.v_divider)

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
        elif width < 1200 or self.forced_compact_mode:
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
        self._safe_update(self.rail)
        if self.bottom_nav.visible:
            self.bottom_nav.selected_index = index
            self._safe_update(self.bottom_nav)
