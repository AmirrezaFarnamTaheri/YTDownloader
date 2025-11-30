import logging

import flet as ft

from theme import Theme

logger = logging.getLogger(__name__)


class AppLayout:
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
        self.content_area = ft.Container(content=initial_view, expand=True, padding=20)

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
        )

        # Clipboard Monitor Toggle
        self.clipboard_switch = ft.Switch(
            label="Clipboard Monitor",
            value=clipboard_active,
            on_change=self._on_clipboard_toggle,
            # label_position=ft.LabelPosition.LEFT # Removed, might not be supported in this flet version stubs
        )

        # Logo / Header
        self.header = ft.Container(
            content=ft.Column(
                [
                    ft.Image(
                        src="assets/logo.svg",
                        width=48,
                        height=48,
                        color=Theme.Primary.MAIN,
                    ),
                    ft.Text(
                        "StreamCatch",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.Text.PRIMARY,
                    ),
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
                ft.VerticalDivider(width=1, color="transparent"),
                self.content_area,
            ],
            expand=True,
            spacing=0,
        )

    def _on_nav_change(self, e):
        index = e.control.selected_index
        logger.info(f"Navigation changed to index: {index}")
        self.navigate_callback(index)

    def _on_clipboard_toggle(self, e):
        logger.info(f"Clipboard monitor toggled to: {e.control.value}")
        self.toggle_clipboard_callback(e.control.value)

    def set_content(self, view_control):
        logger.debug(f"Setting content view: {type(view_control).__name__}")
        self.content_area.content = view_control
        try:
            self.content_area.update()
        except AssertionError:
            # Can happen if called before adding to page
            pass
        except Exception as e:
            logger.warning(f"Failed to update content area: {e}")
