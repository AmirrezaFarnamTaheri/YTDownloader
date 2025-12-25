"""
Download Item Control.

Represents a single download item in the Queue or History list.
Features progress bar, status icon, and action buttons.
"""

import logging
from typing import Any, Callable, Dict

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme

logger = logging.getLogger(__name__)


class DownloadItemControl(ft.Container):
    """
    A card-like control representing a download task.
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments

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

        # Apply standardized card decoration
        card_style = Theme.get_card_decoration()
        for key, value in card_style.items():
            setattr(self, key, value)

        # Override padding if needed or use from decoration
        self.padding = 15  # slightly tighter for list items

        # UI Components
        self.title_text = ft.Text(
            item.get("title", item.get("url", LM.get("unknown_title"))),
            weight=ft.FontWeight.BOLD,
            size=16,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=Theme.Text.PRIMARY,
        )

        # Status Badge
        self.status_text = ft.Text(
            self._get_status_label(item.get("status", "Queued")),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=Theme.Text.PRIMARY,
        )
        self.status_badge = ft.Container(
            content=self.status_text,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
            bgcolor=Theme.BG_HOVER,  # Default
        )

        self.progress_bar = ft.ProgressBar(
            value=item.get("progress", 0),
            color=Theme.Primary.MAIN,
            bgcolor=Theme.Surface.BG,
            height=6,
        )

        self.info_text = ft.Text("", size=11, color=Theme.TEXT_MUTED)

        self.action_row = ft.Row(spacing=0)

        # Main Layout: Row with Icon | Content | Actions
        self.content = ft.Column(
            [
                ft.Row(
                    [
                        # Icon based on URL/Type
                        self._get_platform_icon(item.get("url", "")),
                        ft.Container(width=10),  # Spacer
                        # Title and Info
                        ft.Column(
                            [
                                self.title_text,
                                ft.Row(
                                    [self.status_badge, self.info_text],
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                        # Actions
                        self.action_row,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=5),
                self.progress_bar,
            ],
            spacing=0,
        )

        # Attach to item for updates
        self.item["control"] = self
        self.update_actions()
        self._update_progress_internal(update_ui=False)

    def _get_platform_icon(self, url: str) -> ft.Icon:
        """Returns an icon based on the URL."""
        if "youtube" in url or "youtu.be" in url:
            return ft.Icon(ft.icons.VIDEO_LIBRARY, color=ft.colors.RED_400, size=32)
        if "instagram" in url:
            return ft.Icon(ft.icons.PHOTO_CAMERA, color=ft.colors.PINK_400, size=32)
        if "twitter" in url or "x.com" in url:
            return ft.Icon(ft.icons.ALTERNATE_EMAIL, color=ft.colors.BLUE_400, size=32)
        return ft.Icon(ft.icons.LINK, color=Theme.Primary.MAIN, size=32)

    def update_progress(self):
        """Update progress bar and text (External Call)."""
        self._update_progress_internal(update_ui=True)

    def _update_progress_internal(self, update_ui: bool = True):
        """Internal update logic."""
        status = self.item.get("status", "Unknown")
        progress = self.item.get("progress", 0)

        self.progress_bar.value = progress
        self.status_text.value = self._get_status_label(status)

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
            info_parts.append(f"{LM.get('eta_label')} {eta}")

        self.info_text.value = " | ".join(info_parts)

        # Status Coloring
        if status == "Downloading":
            self.status_badge.bgcolor = ft.colors.with_opacity(0.2, Theme.Primary.MAIN)
            self.status_text.color = Theme.Primary.MAIN
        elif status == "Allocating":
            self.status_badge.bgcolor = ft.colors.with_opacity(0.2, Theme.INFO)
            self.status_text.color = Theme.INFO
        elif status == "Completed":
            self.status_badge.bgcolor = ft.colors.with_opacity(
                0.2, Theme.Status.SUCCESS
            )
            self.status_text.color = Theme.Status.SUCCESS
            self.progress_bar.value = 1.0
            self.progress_bar.color = Theme.Status.SUCCESS
        elif status == "Processing":
            self.status_badge.bgcolor = ft.colors.with_opacity(0.2, Theme.ACCENT)
            self.status_text.color = Theme.ACCENT
        elif status == "Error":
            self.status_badge.bgcolor = ft.colors.with_opacity(0.2, Theme.Status.ERROR)
            self.status_text.color = Theme.Status.ERROR
            self.progress_bar.color = Theme.Status.ERROR
        elif status == "Cancelled":
            self.status_badge.bgcolor = ft.colors.with_opacity(0.2, Theme.TEXT_MUTED)
            self.status_text.color = Theme.TEXT_MUTED
        elif str(status).startswith("Scheduled"):
            self.status_badge.bgcolor = ft.colors.with_opacity(0.2, Theme.WARNING)
            self.status_text.color = Theme.WARNING
        else:
            self.status_badge.bgcolor = Theme.BG_HOVER
            self.status_text.color = Theme.Text.SECONDARY

        self.update_actions()
        if update_ui:
            self.update()

    def update_actions(self):
        """Update available action buttons based on status."""
        status = self.item.get("status", "Unknown")
        self.action_row.controls.clear()

        # Helper to create styled buttons
        def create_action_btn(icon, tooltip, color, on_click):
            return ft.IconButton(
                icon,
                tooltip=tooltip,
                icon_color=color,
                on_click=on_click,
            )

        # Play Button (Completed)
        if status == "Completed":
            self.action_row.controls.append(
                create_action_btn(
                    ft.icons.PLAY_ARROW,
                    LM.get("play"),
                    Theme.Status.SUCCESS,
                    lambda _: self.on_play(self.item),
                )
            )
            self.action_row.controls.append(
                create_action_btn(
                    ft.icons.FOLDER_OPEN,
                    LM.get("open_folder"),
                    Theme.Text.SECONDARY,
                    lambda _: self.on_open_folder(self.item),
                )
            )

        # Cancel Button (Active)
        if status in ("Downloading", "Queued", "Processing", "Allocating") or str(
            status
        ).startswith("Scheduled"):
            self.action_row.controls.append(
                create_action_btn(
                    ft.icons.CANCEL,
                    LM.get("cancel"),
                    Theme.Status.ERROR,
                    lambda _: self.on_cancel(self.item),
                )
            )

        # Retry Button (Error/Cancelled)
        if status in ("Error", "Cancelled"):
            self.action_row.controls.append(
                create_action_btn(
                    ft.icons.REFRESH,
                    LM.get("retry"),
                    Theme.Primary.MAIN,
                    lambda _: self.on_retry(self.item),
                )
            )

        # Remove Button
        self.action_row.controls.append(
            create_action_btn(
                ft.icons.DELETE_OUTLINE,
                LM.get("remove"),
                Theme.TEXT_MUTED,
                lambda _: self.on_remove(self.item),
            )
        )

    def _get_status_label(self, status: str) -> str:
        """Return a localized status label for display."""
        if not status:
            return LM.get("status_unknown")

        if str(status).startswith("Scheduled"):
            label = str(status)
            if "(" in label and ")" in label:
                time_part = label[label.find("(") + 1 : label.rfind(")")]
                if time_part:
                    return LM.get("status_scheduled_time", time_part)
            return LM.get("status_scheduled")

        status_map = {
            "Queued": "status_queued",
            "Allocating": "status_allocating",
            "Downloading": "status_downloading",
            "Processing": "status_processing",
            "Completed": "status_completed",
            "Error": "status_error",
            "Cancelled": "status_cancelled",
        }

        key = status_map.get(status)
        return LM.get(key) if key else str(status)
