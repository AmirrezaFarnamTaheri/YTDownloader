import flet as ft

from theme import Theme


class AppLayout:
    """
    Manages the main application layout, including the NavigationRail and Content Area.
    """

    def __init__(
        self,
        page: ft.Page,
        navigate_callback,
        toggle_clipboard_callback,
        clipboard_active=False,
    ):
        self.page = page
        self.navigate_callback = navigate_callback
        self.toggle_clipboard_callback = toggle_clipboard_callback
        self.clipboard_active = clipboard_active
        self.content_area = ft.Container(expand=True, bgcolor=Theme.BG_DARK)

        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            bgcolor=Theme.BG_CARD,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DOWNLOAD,
                    selected_icon=ft.Icons.DOWNLOAD_DONE,
                    label="Download",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.QUEUE_MUSIC,
                    selected_icon=ft.Icons.QUEUE_MUSIC_ROUNDED,
                    label="Queue",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY,
                    selected_icon=ft.Icons.HISTORY_TOGGLE_OFF,
                    label="History",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD,
                    selected_icon=ft.Icons.DASHBOARD_CUSTOMIZE,
                    label="Dashboard",
                ),
                ft.NavigationRailDestination(icon=ft.Icons.RSS_FEED, label="RSS"),
                ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
            ],
            on_change=lambda e: self.navigate_callback(e.control.selected_index),
        )

        # Clipboard Monitor Toggle
        self.clipboard_switch = ft.Switch(
            label="Clipboard Monitor",
            value=self.clipboard_active,
            active_color=Theme.PRIMARY,
            on_change=self._on_clipboard_change,
        )

        # About / Help Button
        self.about_btn = ft.IconButton(
            ft.Icons.HELP_OUTLINE,
            tooltip="About & Help",
            icon_color=Theme.TEXT_SECONDARY,
            on_click=self.show_about_dialog,
        )

        # Sidebar Footer
        sidebar_content = ft.Column(
            [
                self.nav_rail,
                ft.Container(expand=True),
                ft.Container(
                    padding=20,
                    content=ft.Column(
                        [
                            self.clipboard_switch,
                            ft.Row(
                                [self.about_btn], alignment=ft.MainAxisAlignment.CENTER
                            ),
                        ]
                    ),
                ),
            ],
            width=200,
        )

        self.view = ft.Row(
            [
                sidebar_content,
                ft.VerticalDivider(width=1, color=Theme.BORDER),
                self.content_area,
            ],
            expand=True,
            spacing=0,
        )

    def _on_clipboard_change(self, e):
        self.toggle_clipboard_callback(e.control.value)

    def set_content(self, view_control):
        self.content_area.content = view_control
        self.content_area.update()

    def show_about_dialog(self, e):
        dlg = ft.AlertDialog(
            title=ft.Text("StreamCatch"),
            content=ft.Column(
                [
                    ft.Text("Version: 2.0.0 (Soul Update)"),
                    ft.Text("The ultimate media downloader with a soul."),
                    ft.Divider(),
                    ft.Text("Created by Jules."),
                    ft.Text(
                        "Features: YouTube, Telegram, Twitter, RSS, GPU Accel, Cloud Upload."
                    ),
                    ft.Text("Check WIKI.md for detailed help."),
                ],
                tight=True,
                width=400,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.page.close_dialog())
            ],
        )
        self.page.show_dialog(dlg)
