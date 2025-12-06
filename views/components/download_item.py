"""
Download Item Control.

Represents a single download item in the Queue or History list.
Features progress bar, status icon, and action buttons.
"""

import logging
from typing import Any, Callable, Dict, Optional

import flet as ft

from theme import Theme

logger = logging.getLogger(__name__)


class DownloadItemControl(ft.Container):
    """
    A card-like control representing a download task.
    """

    def __init__(
        self,
        item: Dict[str, Any],
        on_cancel: Callable,
        on_retry: Callable,
        on_remove: Callable,
        on_play: Callable,
        on_open_folder: Callable,
    ):
        super().__init__()
        self.item = item
        self.on_cancel = on_cancel
        self.on_retry = on_retry
        self.on_remove = on_remove
        self.on_play = on_play
        self.on_open_folder = on_open_folder

        # UI Components
        self.title_text = ft.Text(
            item.get("title", item.get("url", "Unknown")),
            weight=ft.FontWeight.BOLD,
            size=16,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=Theme.Text.PRIMARY,
        )

        self.status_text = ft.Text(
            item.get("status", "Queued"),
            size=12,
            color=Theme.Text.SECONDARY,
        )

        self.progress_bar = ft.ProgressBar(
            value=item.get("progress", 0),
            color=Theme.Primary.MAIN,
            bgcolor=Theme.Surface.BG,
            height=6,
            bar_height=6,
        )

        self.info_text = ft.Text("", size=11, color=Theme.TEXT_MUTED)

        self.action_row = ft.Row(spacing=0)

        # Main Layout
        self.content = ft.Column(
            [
                ft.Row(
                    [
                        # Icon based on URL/Type
                        self._get_platform_icon(item.get("url", "")),
                        ft.Column(
                            [self.title_text, self.status_text],
                            spacing=2,
                            expand=True,
                        ),
                        self.action_row,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.progress_bar,
                ft.Row(
                    [self.info_text],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=8,
        )

        self.padding = 15
        self.border_radius = 10
        self.bgcolor = Theme.Surface.CARD
        # self.border = ft.border.all(1, Theme.Divider.COLOR) # Cleaner without border?
        self.shadow = ft.BoxShadow(
            blur_radius=5,
            color=ft.colors.with_opacity(0.05, ft.colors.BLACK),
        )

        # Attach to item for updates
        self.item["control"] = self
        self.update_actions()
        self._update_progress_internal(update_ui=False)

    def _get_platform_icon(self, url: str) -> ft.Icon:
        """Returns an icon based on the URL."""
        if "youtube" in url or "youtu.be" in url:
            return ft.Icon(ft.icons.VIDEO_LIBRARY, color=ft.colors.RED_400, size=30)
        elif "instagram" in url:
            return ft.Icon(ft.icons.PHOTO_CAMERA, color=ft.colors.PINK_400, size=30)
        elif "twitter" in url or "x.com" in url:
            return ft.Icon(ft.icons.ALTERNATE_EMAIL, color=ft.colors.BLUE_400, size=30)
        else:
            return ft.Icon(ft.icons.LINK, color=Theme.Primary.MAIN, size=30)

    def update_progress(self):
        """Update progress bar and text (External Call)."""
        self._update_progress_internal(update_ui=True)

    def _update_progress_internal(self, update_ui: bool = True):
        """Internal update logic."""
        status = self.item.get("status", "Unknown")
        progress = self.item.get("progress", 0)

        self.progress_bar.value = progress
        self.status_text.value = status

        # Detailed info
        speed = self.item.get("speed", "")
        eta = self.item.get("eta", "")
        size = self.item.get("size", "")

        info_parts = []
        if size:
            info_parts.append(size)
        if speed:
            info_parts.append(speed)
        if eta:
            info_parts.append(f"ETA: {eta}")

        self.info_text.value = " • ".join(info_parts)

        # Status Coloring
        if status == "Downloading":
            self.status_text.color = Theme.Primary.MAIN
        elif status == "Completed":
            self.status_text.color = Theme.Status.SUCCESS
            self.progress_bar.value = 1.0
            self.progress_bar.color = Theme.Status.SUCCESS
        elif status == "Error":
            self.status_text.color = Theme.Status.ERROR
            self.progress_bar.color = Theme.Status.ERROR
        else:
            self.status_text.color = Theme.Text.SECONDARY

        self.update_actions()
        if update_ui:
            self.update()

    def update_actions(self):
        """Update available action buttons based on status."""
        status = self.item.get("status", "Unknown")
        self.action_row.controls.clear()

        # Play Button (Completed)
        if status == "Completed":
            self.action_row.controls.append(
                ft.IconButton(
                    ft.icons.PLAY_ARROW,
                    tooltip="Play",
                    icon_color=Theme.Status.SUCCESS,
                    on_click=lambda _: self.on_play(self.item),
                )
            )
            self.action_row.controls.append(
                ft.IconButton(
                    ft.icons.FOLDER_OPEN,
                    tooltip="Open Folder",
                    icon_color=Theme.Text.SECONDARY,
                    on_click=lambda _: self.on_open_folder(self.item),
                )
            )

        # Cancel Button (Active)
        if status in ("Downloading", "Queued", "Processing"):
            self.action_row.controls.append(
                ft.IconButton(
                    ft.icons.CANCEL,
                    tooltip="Cancel",
                    icon_color=Theme.Status.ERROR,
                    on_click=lambda _: self.on_cancel(self.item),
                )
            )

        # Retry Button (Error/Cancelled)
        if status in ("Error", "Cancelled"):
            self.action_row.controls.append(
                ft.IconButton(
                    ft.icons.REFRESH,
                    tooltip="Retry",
                    icon_color=Theme.Primary.MAIN,
                    on_click=lambda _: self.on_retry(self.item),
                )
            )

        # Remove Button (Always available mostly, or specialized)
        # Maybe show 'Close' or 'Delete' icon always?
        self.action_row.controls.append(
            ft.IconButton(
                ft.icons.DELETE_OUTLINE,
                tooltip="Remove",
                icon_color=Theme.TEXT_MUTED,
                on_click=lambda _: self.on_remove(self.item),
            )
        )
