# pylint: disable=unnecessary-lambda,import-outside-toplevel,broad-exception-caught
"""
Download View Module.

Provides the UI for adding new downloads, including URL input,
format selection, and options configuration.
Refactored for responsiveness, better state management, and aesthetics.
"""

import logging
import sys
from collections.abc import Callable

import flet as ft

from app_state import AppState
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import get_default_download_path, open_folder
from views.base_view import BaseView
from views.components.download_input_card import DownloadInputCard
from views.components.download_preview import DownloadPreviewCard

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class DownloadView(BaseView):
    """
    Main view for adding downloads.

    Features:
    - Responsive Layout
    - Dynamic Panels (YouTube, Insta, etc.)
    - Cookie Selection
    - Scheduling & Batch Import
    """

    # pylint: disable=too-many-arguments, too-many-positional-arguments

    def __init__(
        self,
        on_fetch_info: Callable,
        on_add_to_queue: Callable,
        on_batch_import: Callable,
        on_schedule: Callable,
        app_state: AppState,
    ):
        super().__init__(LM.get("new_download"), ft.icons.DOWNLOAD)
        self.on_fetch_info = on_fetch_info
        self.on_add_to_queue = on_add_to_queue
        self.on_batch_import = on_batch_import
        self.on_schedule = on_schedule
        self.state = app_state
        # pylint: disable=unsubscriptable-object
        self.video_info: dict | None = None

        # Input Card
        self.input_card = DownloadInputCard(
            on_fetch=self.on_fetch_info,
            on_paste=self._on_paste_click,
            app_state=self.state,
        )

        # 5. Main Actions
        self.add_btn = ft.ElevatedButton(
            LM.get("add_to_queue"),
            icon=ft.icons.ADD,
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
                            ft.icons.FILE_UPLOAD,
                            tooltip=LM.get("batch_import"),
                            on_click=lambda _: self.on_batch_import(),
                            icon_color=Theme.Text.SECONDARY,
                        ),
                        ft.IconButton(
                            ft.icons.SCHEDULE,
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
                    icon=ft.icons.FOLDER_OPEN,
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
                        self.input_card,
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

    def _on_paste_click(self, e):
        # pylint: disable=unused-argument
        try:
            import pyperclip

            try:
                content = pyperclip.paste()
                if content:
                    self.input_card.set_url(content.strip())
                    self.input_card.url_input.focus()
            except pyperclip.PyperclipException:
                logger.warning("Clipboard access not available")
        except Exception as ex:
            logger.warning("Failed to paste: %s", ex)

    def _on_fetch_click(self, e):
        # Delegated to InputCard, but if invoked here (unused):
        pass

    def _on_add_click(self, e):
        # pylint: disable=unused-argument
        data = self.input_card.get_options()

        # Add output template from global config if not present (although input card doesn't handle template yet)
        template = self.state.config.get("output_template", "%(title)s.%(ext)s")
        data["output_template"] = template

        # Add defaults
        data.setdefault("video_format", "best")
        data.setdefault("audio_format", None)
        data.setdefault("subtitle_lang", None)
        data.setdefault("playlist", False)
        data.setdefault("sponsorblock", False)

        self.on_add_to_queue(data)

        # Reset
        self.add_btn.disabled = True
        self.preview_card.visible = False
        self.input_card.reset()

        self.update()

    # pylint: disable=missing-function-docstring
    def update_video_info(self, info: dict | None):
        self.video_info = info
        self.input_card.update_video_info(info)

        if info:
            self.preview_card.update_info(info)
            self.add_btn.disabled = False
        else:
            self.preview_card.visible = False
            self.add_btn.disabled = True

        # pylint: disable=import-outside-toplevel
        self.update()

    # pylint: disable=missing-function-docstring

    def update_info(self, info: dict | None):
        self.update_video_info(info)

    # pylint: disable=broad-exception-caught
    # pylint: disable=import-outside-toplevel

    def _open_downloads_folder(self):
        from pathlib import Path

        try:
            preferred = self.state.config.get("download_path")
            path = Path(get_default_download_path(preferred))
            if not open_folder(str(path), self.page) and self.page:
                self.page.open(
                    ft.SnackBar(content=ft.Text(LM.get("open_folder_failed")))
                )
        except Exception as e:
            logger.error("Failed to open folder: %s", e)
