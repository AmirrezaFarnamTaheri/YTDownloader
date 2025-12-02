"""
App Layout module.

Defines the main application layout including the sidebar navigation
and content area management.
"""

import logging

import flet as ft

from theme import Theme

logger = logging.getLogger(__name__)


class AppLayout:
    """
    Main application layout component.
    """

    def __init__(
        self,
        page: ft.Page,
        navigate_callback,
        toggle_clipboard_callback,
        clipboard_active=False,
        initial_view=None,
    ):
        self.page = page
        self.navigate_callback = navigate_callback
        self.toggle_clipboard_callback = toggle_clipboard_callback

        # Main content area
        self.content_area = ft.Container(
            content=initial_view,
            expand=True,
            padding=20,
            # Improve background transition if needed, currently transparent
        )

        # Navigation Rail
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DOWNLOAD_OUTLINED,
                    selected_icon=ft.Icons.DOWNLOAD,
                    label="Download",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.QUEUE_MUSIC_OUTLINED,
                    selected_icon=ft.Icons.QUEUE_MUSIC,
                    label="Queue",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED,
                    selected_icon=ft.Icons.HISTORY,
                    label="History",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label="Dashboard",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.RSS_FEED_OUTLINED,
                    selected_icon=ft.Icons.RSS_FEED,
                    label="RSS Feeds",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Settings",
                ),
            ],
            on_change=self._on_nav_change,
            bgcolor=Theme.Surface.BG,
            # Add leading/trailing logic support for mobile collapse
            extended=True,
        )

        # Clipboard Monitor Toggle
        self.clipboard_switch = ft.Switch(
            label="Clipboard Monitor",
            value=clipboard_active,
            on_change=self._on_clipboard_toggle,
        )

        # Logo
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

        # Logo / Header
        self.header = ft.Container(
            content=ft.Column(
                [
                    self.logo_image,
                    self.logo_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            padding=ft.padding.only(top=20, bottom=10),
        )

        # Sidebar container
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
        )

        # Main Layout
        self.view = ft.Row(
            [
                self.sidebar,
                # ft.VerticalDivider(width=1, color="transparent"), # Redundant if sidebar has border
                self.content_area,
            ],
            expand=True,
            spacing=0,
        )

    def _on_nav_change(self, e):
        index = e.control.selected_index
        logger.info("Navigation changed to index: %d", index)
        self.navigate_callback(index)

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
            # Can happen if called before adding to page
            pass
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to update content area: %s", e)

    def set_sidebar_collapsed(self, collapsed: bool):
        """Collapse or expand the sidebar for mobile responsiveness."""
        if collapsed:
            self.rail.extended = False
            self.rail.min_width = 70
            self.rail.label_type = ft.NavigationRailLabelType.NONE
            self.sidebar.width = 70
            self.logo_text.visible = False
            self.clipboard_switch.label = ""  # Hide label
            self.clipboard_switch.tooltip = "Clipboard Monitor"
        else:
            self.rail.extended = True
            self.rail.min_width = 100
            self.rail.label_type = ft.NavigationRailLabelType.ALL
            self.sidebar.width = 200
            self.logo_text.visible = True
            self.clipboard_switch.label = "Clipboard Monitor"
            self.clipboard_switch.tooltip = None

        try:
            self.sidebar.update()
        except Exception:
            pass
