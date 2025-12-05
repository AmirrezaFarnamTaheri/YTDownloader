"""
AppLayout module.
Manages the main layout structure (Sidebar vs. Content) and responsive behavior.
Refactored to support Compact Mode and better responsiveness.
"""

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme


class AppLayout(ft.Row):
    """
    Main application layout using a Row of [Sidebar, Content].
    Supports responsiveness via checking page width (though explicit logic is simpler here).
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
                icon=ft.Icons.DOWNLOAD,
                selected_icon=ft.Icons.DOWNLOAD_ROUNDED,
                label=LM.get("download"),
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.LIST,
                selected_icon=ft.Icons.LIST_ALT,
                label=LM.get("queue"),
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HISTORY,
                selected_icon=ft.Icons.HISTORY_TOGGLE_OFF,
                label=LM.get("history"),
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.RSS_FEED,
                selected_icon=ft.Icons.RSS_FEED_ROUNDED,
                label=LM.get("rss"),
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS,
                selected_icon=ft.Icons.SETTINGS_SUGGEST,
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
            extended=True,
            min_width=72,
            min_extended_width=200,
            group_alignment=-0.9,
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

        self.controls = [
            self.sidebar_container,
            # Using Container instead of VerticalDivider for clearer definition/no issues
            ft.Container(width=1, bgcolor=Theme.DIVIDER),
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

    def set_navigation_index(self, index: int):
        """Sets the selected navigation index programmatically."""
        self.rail.selected_index = index  # type: ignore
        self.rail.update()
