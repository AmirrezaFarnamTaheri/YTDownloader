"""
Download View Module.

Provides the UI for adding new downloads, including URL input,
format selection, and options configuration.
"""

import logging
from typing import Callable, Optional

import flet as ft

from app_state import AppState
from components.download_item import DownloadItemControl
from views.base_view import BaseView
# Corrected import path
from views.components.download_input import DownloadInputCard
from views.components.download_preview import DownloadPreviewCard

logger = logging.getLogger(__name__)


class DownloadView(BaseView):
    """
    Main view for adding downloads.

    Features:
    - URL input with validation
    - Video info fetching and preview
    - Format selection (Video/Audio/Resolution)
    - Advanced options (Playlist, SponsorBlock)
    - Batch import and Scheduling
    """

    def __init__(
        self,
        on_fetch_info: Callable,
        on_add_to_queue: Callable,
        on_batch_import: Callable,
        on_schedule: Callable,
        app_state: AppState,
    ):
        super().__init__("New Download", ft.Icons.DOWNLOAD)
        self.on_fetch_info = on_fetch_info
        self.on_add_to_queue = on_add_to_queue
        self.on_batch_import = on_batch_import
        self.on_schedule = on_schedule
        self.state = app_state
        self.video_info = None

        # --- Controls ---
        self.url_input = ft.TextField(
            label="Video URL",
            hint_text="https://youtube.com/watch?v=...",
            expand=True,
            autofocus=True,
            on_submit=lambda e: self._on_fetch_click(e),
        )

        self.fetch_btn = ft.ElevatedButton(
            "Fetch Info",
            icon=ft.Icons.SEARCH,
            on_click=self._on_fetch_click,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8), padding=20
            ),
        )

        # Options
        self.video_format_dd = ft.Dropdown(
            label="Format",
            width=150,
            options=[
                ft.dropdown.Option("best", "Best Quality"),
                ft.dropdown.Option("audio", "Audio Only (MP3)"),
                ft.dropdown.Option("4k", "4K (2160p)"),
                ft.dropdown.Option("1440p", "1440p"),
                ft.dropdown.Option("1080p", "1080p"),
                ft.dropdown.Option("720p", "720p"),
                ft.dropdown.Option("480p", "480p"),
            ],
            value="best",
        )

        self.playlist_cb = ft.Checkbox(label="Playlist", value=False)
        self.sponsorblock_cb = ft.Checkbox(label="SponsorBlock", value=False)
        self.force_generic_cb = ft.Checkbox(label="Force Generic", value=False)

        self.time_start = ft.TextField(
            label="Start (HH:MM:SS)", width=120, disabled=True
        )
        self.time_end = ft.TextField(
            label="End (HH:MM:SS)", width=120, disabled=True
        )

        self.cookies_dd = ft.Dropdown(
            label="Browser Cookies",
            width=200,
            options=[
                ft.dropdown.Option(None, "None"),
                ft.dropdown.Option("chrome", "Chrome"),
                ft.dropdown.Option("firefox", "Firefox"),
                ft.dropdown.Option("edge", "Edge"),
                ft.dropdown.Option("opera", "Opera"),
                ft.dropdown.Option("brave", "Brave"),
                ft.dropdown.Option("vivaldi", "Vivaldi"),
                ft.dropdown.Option("safari", "Safari"),
            ],
            value=None,
        )

        self.add_btn = ft.ElevatedButton(
            "Add to Queue",
            icon=ft.Icons.ADD,
            on_click=self._on_add_click,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.PRIMARY,
                color=ft.Colors.ON_PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=20,
            ),
        )

        # Info Display
        self.info_container = ft.Column(visible=False, spacing=10)

        # Initialize Layout
        self._build_ui()

    def _build_ui(self):
        """Constructs the UI layout."""
        # Check platform to hide unnecessary buttons on mobile
        import sys
        is_mobile = False
        try:
             # Flet doesn't strictly expose "is_mobile" directly on view init easily without page,
             # but we can infer or wait. Since we are in init, we don't have page yet.
             # We'll use sys.platform for basic desktop checks, else assume mobile if appropriate?
             # No, better to keep it generic or check later.
             # However, "Open Downloads Folder" is strictly desktop.
             # We can check simple OS indicators.
             if sys.platform not in ("win32", "linux", "darwin"):
                 is_mobile = True
        except Exception:
             pass

        # Header with actions
        header = ft.Row(
            [
                ft.Text("New Download", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.FILE_UPLOAD,
                    tooltip="Batch Import URLs",
                    on_click=lambda e: self.on_batch_import(),
                ),
                ft.IconButton(
                    icon=ft.Icons.SCHEDULE,
                    tooltip="Schedule Download",
                    on_click=lambda e: self.on_schedule(e),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Input Section using Components
        input_card = DownloadInputCard(
            self.url_input,
            self.fetch_btn,
            self.video_format_dd,
            self.cookies_dd,
            self.playlist_cb,
            self.sponsorblock_cb,
            self.force_generic_cb,
            self.time_start,
            self.time_end,
        )

        # Preview Section (Hidden initially)
        self.preview_card = DownloadPreviewCard()

        # Action Buttons
        actions_row = ft.Row(
            [
                ft.Container(expand=True),
                self.add_btn,
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        # Utilities Row (Open Folder) - Hide on likely mobile
        utils_row = ft.Row([], alignment=ft.MainAxisAlignment.END)
        if not is_mobile:
            utils_row.controls.append(
                ft.TextButton(
                    "Open Downloads Folder",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda e: self._open_downloads_folder(),
                )
            )

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        header,
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        input_card,
                        self.preview_card,
                        actions_row,
                        ft.Divider(),
                        utils_row,
                    ],
                    spacing=20,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
                expand=True,
            )
        ]

    def _on_fetch_click(self, e):
        """Handle fetch info click."""
        url = self.url_input.value
        if url:
            self.fetch_btn.disabled = True
            self.update()
            self.on_fetch_info(url)

    def _on_add_click(self, e):
        """Handle add to queue click."""
        if not self.url_input.value:
            return

        cookies = self.cookies_dd.value
        if cookies == "None":
            cookies = None

        # Retrieve output template from config
        config_template = self.state.config.get("output_template", "%(title)s.%(ext)s")

        data = {
            "url": self.url_input.value,
            "video_format": self.video_format_dd.value,
            "playlist": self.playlist_cb.value,
            "sponsorblock": self.sponsorblock_cb.value,
            "force_generic": self.force_generic_cb.value,
            "start_time": self.time_start.value,
            "end_time": self.time_end.value,
            "output_template": config_template,
            "cookies_from_browser": cookies,
        }
        self.on_add_to_queue(data)

    def update_video_info(self, info: Optional[dict]):
        """Update the UI with fetched video info."""
        self.fetch_btn.disabled = False
        self.video_info = info

        if info:
            self.preview_card.update_info(info)
            self.add_btn.disabled = False
            self.time_start.disabled = False
            self.time_end.disabled = False

            # Auto-detect if it looks like a playlist
            if info.get("_type") == "playlist" or "entries" in info:
                self.playlist_cb.value = True
        else:
            self.preview_card.visible = False
            self.add_btn.disabled = True
            self.time_start.disabled = True
            self.time_end.disabled = True

        self.update()

    def _open_downloads_folder(self):
        """Opens the downloads folder in file explorer."""
        from ui_utils import open_folder
        from pathlib import Path

        # Try to resolve default path again or from config if we had one
        path = Path.home() / "Downloads"
        open_folder(str(path))
