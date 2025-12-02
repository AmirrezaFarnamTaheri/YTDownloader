"""
Download View Module.

Provides the UI for adding new downloads, including URL input,
format selection, and options configuration.
Refactored for responsiveness, better state management, and aesthetics.
"""

import logging
import sys
from typing import Callable, Optional

import flet as ft

from app_state import AppState
from views.base_view import BaseView
from views.components.download_input import DownloadInputCard
from views.components.download_preview import DownloadPreviewCard
from theme import Theme

logger = logging.getLogger(__name__)


class DownloadView(BaseView):
    """
    Main view for adding downloads.

    Features:
    - Responsive Layout
    - Advanced Options (Subtitle, Audio Selection)
    - Cookie Selection
    - Scheduling & Batch Import
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
        # 1. URL Input
        self.url_input = ft.TextField(
            label="Video URL",
            hint_text="https://youtube.com/watch?v=...",
            expand=True,
            autofocus=True,
            border_radius=8,
            on_submit=lambda e: self._on_fetch_click(e),
            prefix_icon=ft.Icons.LINK,
            bgcolor=Theme.Surface.INPUT,
        )

        self.fetch_btn = ft.ElevatedButton(
            "Fetch Info",
            icon=ft.Icons.SEARCH,
            on_click=self._on_fetch_click,
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=Theme.Primary.MAIN,
                color=Theme.Text.PRIMARY,
            ),
        )

        # 2. Basic Options
        self.video_format_dd = ft.Dropdown(
            label="Format",
            width=180,
            border_radius=8,
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
            bgcolor=Theme.Surface.INPUT,
        )

        self.audio_format_dd = ft.Dropdown(
            label="Audio Stream",
            width=180,
            border_radius=8,
            visible=False,
            bgcolor=Theme.Surface.INPUT,
        )

        self.subtitle_dd = ft.Dropdown(
            label="Subtitles",
            width=180,
            border_radius=8,
            options=[
                ft.dropdown.Option("None", "None"),
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("es", "Spanish"),
                ft.dropdown.Option("fr", "French"),
                ft.dropdown.Option("de", "German"),
                ft.dropdown.Option("ja", "Japanese"),
                ft.dropdown.Option("auto", "Auto-generated"),
            ],
            value="None",
            bgcolor=Theme.Surface.INPUT,
        )

        # 3. Switches & Checkboxes
        self.playlist_cb = ft.Checkbox(label="Playlist", value=False)
        self.sponsorblock_cb = ft.Checkbox(label="SponsorBlock", value=False)
        self.force_generic_cb = ft.Checkbox(label="Force Generic", value=False)

        # 4. Advanced (Time / Cookies)
        self.time_start = ft.TextField(
            label="Start (HH:MM:SS)",
            width=140,
            disabled=True,
            border_radius=8,
            text_size=12,
            bgcolor=Theme.Surface.INPUT,
        )
        self.time_end = ft.TextField(
            label="End (HH:MM:SS)",
            width=140,
            disabled=True,
            border_radius=8,
            text_size=12,
            bgcolor=Theme.Surface.INPUT,
        )

        self.cookies_dd = ft.Dropdown(
            label="Browser Cookies",
            width=200,
            border_radius=8,
            options=[
                ft.dropdown.Option("None", "None"),
                ft.dropdown.Option("chrome", "Chrome"),
                ft.dropdown.Option("firefox", "Firefox"),
                ft.dropdown.Option("edge", "Edge"),
            ],
            value="None",
            bgcolor=Theme.Surface.INPUT,
        )

        # 5. Main Actions
        self.add_btn = ft.ElevatedButton(
            "Add to Queue",
            icon=ft.Icons.ADD,
            on_click=self._on_add_click,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor=Theme.Status.SUCCESS,
                color=Theme.Text.PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=20,
                elevation=2,
            ),
        )

        # Preview Card Component
        self.preview_card = DownloadPreviewCard()

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Constructs the UI layout."""

        # Header
        header = ft.Row(
            [
                ft.Column([
                    ft.Text("New Download", style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD),
                    ft.Text("Enter a URL to start downloading", style=ft.TextThemeStyle.BODY_MEDIUM, color=Theme.Text.SECONDARY),
                ], spacing=2),
                ft.Row([
                    ft.IconButton(ft.Icons.FILE_UPLOAD, tooltip="Batch Import", on_click=lambda _: self.on_batch_import()),
                    ft.IconButton(ft.Icons.SCHEDULE, tooltip="Schedule", on_click=lambda e: self.on_schedule(e)),
                ])
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Input Area
        url_row = ft.Row(
            [self.url_input, self.fetch_btn],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Options Grid
        # Use a Wrap for responsiveness
        options_row = ft.Row(
            [
                self.video_format_dd,
                self.audio_format_dd,
                self.subtitle_dd,
                self.cookies_dd,
            ],
            wrap=True,
            spacing=15,
            run_spacing=15,
        )

        switches_row = ft.Row(
            [self.playlist_cb, self.sponsorblock_cb, self.force_generic_cb],
            wrap=True,
            spacing=20
        )

        time_row = ft.Row(
            [self.time_start, self.time_end],
            spacing=10
        )

        # Input Card Container
        input_container = ft.Container(
            content=ft.Column(
                [
                    url_row,
                    ft.Divider(height=20, color="transparent"),
                    ft.Text("Options", weight=ft.FontWeight.BOLD),
                    options_row,
                    switches_row,
                    ft.Divider(height=10, color="transparent"),
                    ft.Text("Advanced", weight=ft.FontWeight.BOLD),
                    ft.Row([time_row], wrap=True),
                ],
                spacing=10
            ),
            bgcolor=Theme.Surface.CARD,
            padding=20,
            border_radius=12,
            border=ft.border.all(1, Theme.Divider.COLOR),
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
            )
        )

        # Actions
        actions_bar = ft.Row(
            [
                ft.Container(expand=True),
                self.add_btn
            ],
            alignment=ft.MainAxisAlignment.END
        )

        # Footer Actions (Desktop Only)
        footer = ft.Row([], alignment=ft.MainAxisAlignment.END)
        if sys.platform in ("win32", "linux", "darwin"):
            footer.controls.append(
                ft.TextButton(
                    "Open Downloads Folder",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda _: self._open_downloads_folder()
                )
            )

        # Main Layout
        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        header,
                        ft.Divider(color="transparent", height=10),
                        input_container,
                        self.preview_card,
                        ft.Divider(color="transparent", height=10),
                        actions_bar,
                        ft.Divider(),
                        footer
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=15,
                ),
                padding=20,
                expand=True
            )
        ]

    def _on_fetch_click(self, e):
        url = self.url_input.value.strip()
        if url:
            self.fetch_btn.disabled = True
            self.url_input.error_text = None
            self.update()
            self.on_fetch_info(url)
        else:
            self.url_input.error_text = "URL is required"
            self.update()

    def _on_add_click(self, e):
        if not self.url_input.value:
            return

        cookies = self.cookies_dd.value if self.cookies_dd.value != "None" else None
        template = self.state.config.get("output_template", "%(title)s.%(ext)s")

        data = {
            "url": self.url_input.value,
            "video_format": self.video_format_dd.value,
            "audio_format": self.audio_format_dd.value,
            "subtitle_lang": self.subtitle_dd.value if self.subtitle_dd.value != "None" else None,
            "playlist": self.playlist_cb.value,
            "sponsorblock": self.sponsorblock_cb.value,
            "force_generic": self.force_generic_cb.value,
            "start_time": self.time_start.value,
            "end_time": self.time_end.value,
            "output_template": template,
            "cookies_from_browser": cookies,
        }
        self.on_add_to_queue(data)

        # Reset specific fields
        self.add_btn.disabled = True
        self.fetch_btn.disabled = False
        self.preview_card.visible = False
        self.url_input.value = ""
        self.update()

    def update_video_info(self, info: Optional[dict]):
        self.fetch_btn.disabled = False
        self.video_info = info

        if info:
            self.preview_card.update_info(info)
            self.add_btn.disabled = False
            self.time_start.disabled = False
            self.time_end.disabled = False

            # Update formats dynamically
            if "video_streams" in info:
                opts = []
                for s in info["video_streams"]:
                    label = f"{s.get('resolution', '?')} {s.get('ext','')} {s.get('filesize_str','')}"
                    opts.append(ft.dropdown.Option(s['format_id'], label))
                if opts:
                    self.video_format_dd.options = opts
                    self.video_format_dd.value = opts[0].key

            if "audio_streams" in info:
                opts = []
                for s in info["audio_streams"]:
                     label = f"{s.get('abr','?')}k {s.get('ext','')}"
                     opts.append(ft.dropdown.Option(s['format_id'], label))
                if opts:
                    self.audio_format_dd.options = opts
                    self.audio_format_dd.value = opts[0].key
                    self.audio_format_dd.visible = True
            else:
                self.audio_format_dd.visible = False

            if info.get("_type") == "playlist" or "entries" in info:
                self.playlist_cb.value = True
        else:
            self.preview_card.visible = False
            self.add_btn.disabled = True
            self.time_start.disabled = True
            self.time_end.disabled = True
            self.audio_format_dd.visible = False

        self.update()

    def update_info(self, info: Optional[dict]):
        self.update_video_info(info)

    def _open_downloads_folder(self):
        from ui_utils import open_folder
        from pathlib import Path
        try:
            path = Path.home() / "Downloads"
            open_folder(str(path))
        except Exception as e:
            logger.error("Failed to open folder: %s", e)
