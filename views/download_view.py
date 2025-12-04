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
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import open_folder
from views.base_view import BaseView
from views.components.download_preview import DownloadPreviewCard
from views.components.panels.base_panel import BasePanel
from views.components.panels.generic_panel import GenericPanel
from views.components.panels.instagram_panel import InstagramPanel
from views.components.panels.youtube_panel import YouTubePanel

logger = logging.getLogger(__name__)


class DownloadView(BaseView):
    """
    Main view for adding downloads.

    Features:
    - Responsive Layout
    - Dynamic Panels (YouTube, Insta, etc.)
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
        super().__init__(LM.get("new_download"), ft.Icons.DOWNLOAD)
        self.on_fetch_info = on_fetch_info
        self.on_add_to_queue = on_add_to_queue
        self.on_batch_import = on_batch_import
        self.on_schedule = on_schedule
        self.state = app_state
        # pylint: disable=unsubscriptable-object
        self.video_info: Optional[dict] = None
        self.current_panel: Optional[BasePanel] = None

        # --- Controls ---
        # 1. URL Input
        self.url_input = ft.TextField(
            label=LM.get("video_url_label"),
            expand=True,
            autofocus=True,
            on_submit=lambda e: self._on_fetch_click(e),
            **Theme.get_input_decoration(
                hint_text=LM.get("url_placeholder"), prefix_icon=ft.Icons.LINK
            )
        )

        self.fetch_btn = ft.ElevatedButton(
            LM.get("fetch_info"),
            icon=ft.Icons.SEARCH,
            on_click=self._on_fetch_click,
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=Theme.Primary.MAIN,
                color=Theme.Text.PRIMARY,
            ),
        )

        # 2. Dynamic Options Panel Container
        self.options_container = ft.Container()

        # 3. Global Advanced (Time / Cookies)
        self.time_start = ft.TextField(
            label=LM.get("time_start"),
            width=140,
            disabled=True,
            text_size=12,
            **Theme.get_input_decoration(hint_text="00:00:00")
        )
        self.time_end = ft.TextField(
            label=LM.get("time_end"),
            width=140,
            disabled=True,
            text_size=12,
            **Theme.get_input_decoration(hint_text="00:00:00")
        )

        self.cookies_dd = ft.Dropdown(
            label=LM.get("browser_cookies"),
            width=200,
            options=[
                ft.dropdown.Option("None", "None"),
                ft.dropdown.Option("chrome", "Chrome"),
                ft.dropdown.Option("firefox", "Firefox"),
                ft.dropdown.Option("edge", "Edge"),
            ],
            value="None",
            **Theme.get_input_decoration(hint_text="Select Cookies")
        )

        self.force_generic_cb = ft.Checkbox(label=LM.get("force_generic"), value=False)

        # 5. Main Actions
        self.add_btn = ft.ElevatedButton(
            LM.get("add_to_queue"),
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

        # Header - Responsive wrap
        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            LM.get("new_download"),
                            theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                            weight=ft.FontWeight.BOLD,
                            color=Theme.Text.PRIMARY,
                        ),
                        ft.Text(
                            LM.get("enter_url_desc"),
                            theme_style=ft.TextThemeStyle.BODY_MEDIUM,
                            color=Theme.Text.SECONDARY,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Row(
                    [
                        ft.IconButton(
                            ft.Icons.FILE_UPLOAD,
                            tooltip=LM.get("batch_import"),
                            on_click=lambda _: self.on_batch_import(),
                            icon_color=Theme.Text.SECONDARY,
                        ),
                        ft.IconButton(
                            ft.Icons.SCHEDULE,
                            tooltip=LM.get("schedule_download"),
                            on_click=lambda e: self.on_schedule(e),
                            icon_color=Theme.Text.SECONDARY,
                        ),
                    ],
                    wrap=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.START,
            wrap=True,
        )

        # Input Area
        url_row = ft.Row(
            [self.url_input, self.fetch_btn],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        advanced_row = ft.Row(
            [self.time_start, self.time_end, self.cookies_dd], spacing=10, wrap=True
        )

        # Input Card Container
        input_container = ft.Container(
            content=ft.Column(
                [
                    url_row,
                    ft.Divider(height=20, color=Theme.Divider.COLOR),
                    # Dynamic Options Panel
                    self.options_container,
                    ft.Divider(height=10, color="transparent"),
                    # Advanced Collapsible (Simplified for now)
                    ft.ExpansionTile(
                        title=ft.Text(
                            LM.get("advanced_options"), weight=ft.FontWeight.BOLD
                        ),
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    [advanced_row, self.force_generic_cb], spacing=10
                                ),
                                padding=10,
                            )
                        ],
                        collapsed_text_color=Theme.Text.SECONDARY,
                        text_color=Theme.Primary.MAIN,
                        icon_color=Theme.Primary.MAIN,
                    ),
                ],
                spacing=10,
            ),
            bgcolor=Theme.Surface.CARD,
            padding=20,
            border_radius=12,
            border=ft.border.all(1, Theme.Divider.COLOR),
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
            ),
        )

        # Actions
        actions_bar = ft.Row(
            [ft.Container(expand=True), self.add_btn],
            alignment=ft.MainAxisAlignment.END,
        )

        # Footer Actions (Desktop Only)
        footer = ft.Row([], alignment=ft.MainAxisAlignment.END)
        if sys.platform in ("win32", "linux", "darwin"):
            footer.controls.append(
                ft.TextButton(
                    LM.get("open_downloads_folder"),
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda _: self._open_downloads_folder(),
                    style=ft.ButtonStyle(color=Theme.TEXT_MUTED),
                )
            )

        # Main Layout
        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        header,
                        ft.Container(height=10),
                        input_container,
                        self.preview_card,
                        ft.Container(height=10),
                        actions_bar,
                        ft.Divider(color=Theme.Divider.COLOR),
                        footer,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=15,
                ),
                padding=20,
                expand=True,
            )
        ]

    def _on_fetch_click(self, e):
        # pylint: disable=unused-argument
        url = self.url_input.value.strip() if self.url_input.value else ""
        if url:
            self.fetch_btn.disabled = True
            self.url_input.error_text = None
            self.update()
            self.on_fetch_info(url)
        else:
            self.url_input.error_text = LM.get("url_required")
            self.update()

    def _on_add_click(self, e):
        # pylint: disable=unused-argument
        if not self.url_input.value:
            return

        cookies = self.cookies_dd.value if self.cookies_dd.value != "None" else None
        template = self.state.config.get("output_template", "%(title)s.%(ext)s")

        # Get base options
        data = {
            "url": self.url_input.value,
            "start_time": self.time_start.value,
            "end_time": self.time_end.value,
            "output_template": template,
            "cookies_from_browser": cookies,
            "force_generic": self.force_generic_cb.value,
            # Defaults
            "video_format": "best",
            "audio_format": None,
            "subtitle_lang": None,
            "playlist": False,
            "sponsorblock": False,
        }

        # Merge with Panel Options
        if self.current_panel:
            panel_opts = self.current_panel.get_options()
            data.update(panel_opts)

        self.on_add_to_queue(data)

        # Reset specific fields
        self.add_btn.disabled = True
        self.fetch_btn.disabled = False
        self.preview_card.visible = False
        self.url_input.value = ""
        # Clear panel
        self.options_container.content = None
        self.current_panel = None

        self.update()

    def update_video_info(self, info: Optional[dict]):
        self.fetch_btn.disabled = False
        self.video_info = info

        if info:
            self.preview_card.update_info(info)
            self.add_btn.disabled = False
            self.time_start.disabled = False
            self.time_end.disabled = False

            # Determine Panel Type
            url = info.get("original_url", "")
            extractor = info.get("extractor", "").lower()

            # Simple heuristic
            if "youtube" in url or "youtu.be" in url:
                self.current_panel = YouTubePanel(info, lambda: None)
            elif "instagram" in url:
                self.current_panel = InstagramPanel(info, lambda: None)
            else:
                self.current_panel = GenericPanel(info, lambda: None)

            self.options_container.content = self.current_panel

        else:
            self.preview_card.visible = False
            self.add_btn.disabled = True
            self.time_start.disabled = True
            self.time_end.disabled = True
            self.options_container.content = None
            self.current_panel = None

        self.update()

    def update_info(self, info: Optional[dict]):
        self.update_video_info(info)

    def _open_downloads_folder(self):
        from pathlib import Path

        try:
            path = Path.home() / "Downloads"
            open_folder(str(path), self.page)
        except Exception as e:
            logger.error("Failed to open folder: %s", e)
