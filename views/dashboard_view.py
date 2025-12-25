"""
Dashboard View Module.

Features a modern dashboard with system status, quick actions,
active download summaries, and recent history.
"""

import shutil
from typing import Callable

import flet as ft

from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import open_folder
from views.base_view import BaseView
from views.components.history_item import HistoryItemControl


class DashboardView(BaseView):
    """
    Dashboard view serving as the home screen.
    """

    def __init__(
        self,
        on_navigate: Callable,
        on_paste_url: Callable,
        on_batch_import: Callable,
        queue_manager,
    ):
        super().__init__(LM.get("dashboard"), ft.icons.DASHBOARD)
        self.on_navigate = on_navigate
        self.on_paste_url = on_paste_url
        self.on_batch_import = on_batch_import
        self.queue_manager = queue_manager

        # Widgets
        self.status_cards_row = ft.Row(spacing=20, wrap=True)
        self.storage_progress = ft.ProgressBar(
            value=0, color=Theme.Primary.MAIN, bgcolor=Theme.Surface.BG
        )
        self.storage_text = ft.Text(
            LM.get("storage_calculating"), size=12, color=Theme.TEXT_MUTED
        )

        self.recent_history_list = ft.Column(spacing=10)

        self.content_area = ft.Container(
            content=ft.Column(
                [
                    # Welcome & Quick Actions
                    self._build_header_section(),
                    ft.Container(height=20),
                    # System Status (Disk, etc)
                    self._build_status_section(),
                    ft.Container(height=20),
                    # Recent History
                    ft.Text(
                        LM.get("recent_history", "Recent History"),
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.Text.PRIMARY,
                    ),
                    ft.Container(
                        content=self.recent_history_list, **Theme.get_card_decoration()
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=10,
        )

        self.controls = [self.content_area]

    def _build_header_section(self):
        """Builds the top section with Greeting and Quick Actions."""

        # Quick Action Button Helper
        def quick_btn(icon, text, on_click, color):
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icon, size=32, color=color),
                        ft.Text(
                            text, weight=ft.FontWeight.BOLD, color=Theme.Text.PRIMARY
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=160,
                height=100,
                **Theme.get_card_decoration(),
                on_click=on_click,
                ink=True,
            )

        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            LM.get("dashboard_welcome", "Welcome back!"),
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=Theme.Text.PRIMARY,
                        ),
                        ft.Text(
                            LM.get(
                                "dashboard_subtitle", "Ready to download something new?"
                            ),
                            size=16,
                            color=Theme.TEXT_SECONDARY,
                        ),
                    ],
                    expand=True,
                ),
                # Index 1 is Download View
                quick_btn(
                    ft.icons.ADD_LINK,
                    LM.get("quick_download", "New Download"),
                    lambda _: self.on_navigate(1),
                    Theme.ACCENT,
                ),
                quick_btn(
                    ft.icons.FILE_UPLOAD,
                    LM.get("batch_import"),
                    lambda _: self.on_batch_import(),
                    Theme.ACCENT_SECONDARY,
                ),
            ],
            wrap=True,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_status_section(self):
        """Builds system status section."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        LM.get("system_status", "System Storage"),
                        weight=ft.FontWeight.BOLD,
                        color=Theme.Text.PRIMARY,
                    ),
                    self.storage_progress,
                    self.storage_text,
                ],
                spacing=5,
            ),
            **Theme.get_card_decoration(),
        )

    def load(self):
        """Refreshes the dashboard data."""
        self._refresh_storage()
        self._refresh_history()
        if self.page:
            self.update()

    def _refresh_storage(self):
        """Updates storage usage bar."""
        try:
            total, used, free = shutil.disk_usage(".")
            percent = used / total

            gb = 1024**3
            self.storage_progress.value = percent

            # Color logic
            if percent > 0.9:
                self.storage_progress.color = Theme.Status.ERROR
            elif percent > 0.75:
                self.storage_progress.color = Theme.Status.WARNING
            else:
                self.storage_progress.color = Theme.Status.SUCCESS

            self.storage_text.value = LM.get(
                "storage_usage", used / gb, total / gb, free / gb
            )
        except Exception:
            self.storage_text.value = LM.get("storage_info_unavailable")

    def _refresh_history(self):
        """Updates recent history list."""
        items = HistoryManager.get_history(limit=3)
        self.recent_history_list.controls.clear()

        if not items:
            self.recent_history_list.controls.append(
                ft.Text(
                    LM.get("no_recent_downloads"),
                    italic=True,
                    color=Theme.TEXT_MUTED,
                )
            )
        else:
            for item in items:
                ctrl = HistoryItemControl(
                    item,
                    on_open_folder=self._open_history_folder,
                    on_copy_url=self._copy_history_url,
                    on_delete=lambda x: None,
                )
                self.recent_history_list.controls.append(ctrl)

    def _open_history_folder(self, path: str):
        """Open the download folder for a history item."""
        if path and self.page:
            open_folder(path, self.page)

    def _copy_history_url(self, url: str):
        """Copy the URL for a history item."""
        if url and self.page:
            self.page.set_clipboard(url)
