"""
Download Input Card component.
Contains the URL input, fetch button, and download options.
"""

import logging
import re
from collections.abc import Callable

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import normalize_download_target
from views.components.panels.base_panel import BasePanel
from views.components.panels.generic_panel import GenericPanel
from views.components.panels.instagram_panel import InstagramPanel
from views.components.panels.youtube_panel import YouTubePanel

logger = logging.getLogger(__name__)


class DownloadInputCard(ft.Container):
    """
    Card containing download input controls and options.
    """

    def __init__(
        self,
        on_fetch: Callable,
        on_paste: Callable,
        app_state,
        on_options_changed: Callable | None = None,
    ):
        super().__init__()
        self.on_fetch = on_fetch
        self.on_paste_callback = on_paste
        self.state = app_state
        self.on_options_changed = on_options_changed
        self.current_panel: BasePanel | None = None
        self._default_output_template = self._get_default_output_template()

        # --- Controls ---
        self.profile_dd = ft.Dropdown(
            label=LM.get("download_profile"),
            width=220,
            value="best",
            options=[
                ft.dropdown.Option("best", LM.get("profile_best")),
                ft.dropdown.Option("fast_720p", LM.get("profile_fast_720p")),
                ft.dropdown.Option("audio_mp3", LM.get("profile_audio_mp3")),
                ft.dropdown.Option("archive", LM.get("profile_archive")),
            ],
            on_change=self._on_profile_change,
            tooltip=LM.get("download_profile_tooltip"),
            **Theme.get_input_decoration(
                hint_text=LM.get("download_profile"), prefix_icon=ft.icons.TUNE_ROUNDED
            ),
        )

        self.profile_hint = ft.Text(
            LM.get("profile_best_hint"),
            size=12,
            color=Theme.TEXT_MUTED,
        )

        # 1. URL Input
        self.url_input = ft.TextField(
            label=LM.get("video_url_label"),
            expand=True,
            autofocus=True,
            on_submit=lambda e: self._on_fetch_click(e),
            tooltip=LM.get("video_url_tooltip", "Enter URL or search query"),
            suffix=ft.IconButton(
                icon=ft.icons.CONTENT_PASTE_ROUNDED,
                tooltip=LM.get("paste_from_clipboard"),
                on_click=self._on_paste_click,
            ),
            **Theme.get_input_decoration(
                hint_text=LM.get("url_placeholder"), prefix_icon=ft.icons.LINK_ROUNDED
            ),
        )

        self.fetch_btn = ft.ElevatedButton(
            LM.get("fetch_info"),
            icon=ft.icons.SEARCH_ROUNDED,
            on_click=self._on_fetch_click,
            tooltip=LM.get("fetch_info_tooltip", "Fetch video metadata"),
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=Theme.Primary.MAIN,
                color=Theme.Text.PRIMARY,
            ),
        )

        # 2. Dynamic Options Panel Container
        self.options_container = ft.Container(animate_opacity=300)

        # 3. Global Advanced (Time / Cookies)
        self.time_start = ft.TextField(
            label=LM.get("time_start"),
            width=140,
            disabled=True,
            text_size=12,
            tooltip=LM.get("time_start_tooltip", "Start time (HH:MM:SS)"),
            **Theme.get_input_decoration(hint_text=LM.get("time_placeholder")),
        )
        self.time_end = ft.TextField(
            label=LM.get("time_end"),
            width=140,
            disabled=True,
            text_size=12,
            tooltip=LM.get("time_end_tooltip", "End time (HH:MM:SS)"),
            **Theme.get_input_decoration(hint_text=LM.get("time_placeholder")),
        )

        self.cookies_dd = ft.Dropdown(
            label=LM.get("browser_cookies"),
            width=200,
            options=[
                ft.dropdown.Option("None", LM.get("none")),
                ft.dropdown.Option("chrome", LM.get("browser_chrome")),
                ft.dropdown.Option("firefox", LM.get("browser_firefox")),
                ft.dropdown.Option("edge", LM.get("browser_edge")),
            ],
            value="None",
            tooltip=LM.get("cookies_tooltip", "Use cookies from browser"),
            **Theme.get_input_decoration(hint_text=LM.get("select_cookies")),
        )

        self.force_generic_cb = ft.Checkbox(
            label=LM.get("force_generic"),
            value=False,
            tooltip=LM.get(
                "force_generic_tooltip",
                "Force generic downloader (skip specialized extraction)",
            ),
        )

        self.output_template_input = ft.TextField(
            label=LM.get("output_template"),
            value=self._default_output_template,
            expand=True,
            tooltip=LM.get("output_template_tooltip"),
            **Theme.get_input_decoration(
                hint_text="%(title)s.%(ext)s",
                prefix_icon=ft.icons.TEXT_FIELDS_ROUNDED,
            ),
        )

        self._build_ui()

    def _get_default_output_template(self) -> str:
        try:
            config = getattr(self.state, "config", {})
            value = config.get("output_template", "%(title)s.%(ext)s")
            if isinstance(value, str) and value.strip():
                return value
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return "%(title)s.%(ext)s"

    def _build_ui(self):
        # Input Area
        url_row = ft.Row(
            [self.url_input, self.fetch_btn],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        advanced_row = ft.Row(
            [self.time_start, self.time_end, self.cookies_dd],
            spacing=10,
            wrap=True,
        )

        profile_row = ft.Row(
            [
                self.profile_dd,
                ft.Container(
                    content=self.profile_hint,
                    padding=ft.padding.only(top=8),
                    expand=True,
                ),
            ],
            spacing=10,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Advanced Options Section using ExpansionTile
        advanced_section = ft.ExpansionTile(
            title=ft.Text(LM.get("advanced_options"), weight=ft.FontWeight.BOLD),
            controls=[
                ft.Container(
                    content=ft.Column(
                        [advanced_row, self.output_template_input, self.force_generic_cb],
                        spacing=10,
                    ),
                    padding=10,
                )
            ],
            collapsed_text_color=Theme.Text.SECONDARY,
            text_color=Theme.Primary.MAIN,
            icon_color=Theme.Primary.MAIN,
        )

        # Input Card Container with standardized decoration
        input_container_props = Theme.get_card_decoration()

        # Configure self (Container)
        self.content = ft.Column(
            [
                url_row,
                profile_row,
                ft.Divider(height=1, color=Theme.Divider.COLOR),
                # Dynamic Options Panel
                self.options_container,
                ft.Container(height=10),
                # Advanced Options Section
                advanced_section,
            ],
            spacing=10,
        )
        # Apply theme props
        for k, v in input_container_props.items():
            setattr(self, k, v)

    def _on_paste_click(self, e):
        # Delegate to parent/controller logic via callback
        if self.on_paste_callback:
            self.on_paste_callback(e)

    def _on_profile_change(self, e):
        # pylint: disable=unused-argument
        profile = self.profile_dd.value or "best"
        hints = {
            "best": LM.get("profile_best_hint"),
            "fast_720p": LM.get("profile_fast_720p_hint"),
            "audio_mp3": LM.get("profile_audio_mp3_hint"),
            "archive": LM.get("profile_archive_hint"),
        }
        self.profile_hint.value = hints.get(profile, hints["best"])

        if self.current_panel and hasattr(self.current_panel, "apply_profile"):
            self.current_panel.apply_profile(profile)
        self.update()

    # pylint: disable=unused-argument
    def _on_fetch_click(self, e):
        url = self.url_input.value.strip() if self.url_input.value else ""
        if url:
            target = normalize_download_target(url)
            if not target:
                self.url_input.error_text = LM.get("error_invalid_url")
                self.update()
                return

            if target != url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
                logger.info("Non-URL input detected, using ytsearch1 prefix: %s", url)

            self.fetch_btn.disabled = True
            self.url_input.error_text = None
            self.update()
            self.on_fetch(target)
        else:
            self.url_input.error_text = LM.get("url_required")
            self.update()

    def set_url(self, url: str):
        """Sets the URL input value."""
        self.url_input.value = url
        self.url_input.error_text = None
        self.update()

    def trigger_auto_fetch(self):
        """Triggers the fetch action automatically."""
        if not self.url_input.value:
            return
        # Debounce or direct call
        # Since this is UI thread, direct call is fine as fetch is async
        self._on_fetch_click(None)

    def set_fetch_disabled(self, disabled: bool):
        """Enables/disables the fetch button."""
        self.fetch_btn.disabled = disabled
        self.update()

    def reset(self):
        """Resets the input fields."""
        self.url_input.value = ""
        self.options_container.content = None
        self.current_panel = None
        self.fetch_btn.disabled = False
        self.time_start.disabled = True
        self.time_start.value = ""
        self.time_end.disabled = True
        self.time_end.value = ""
        self.output_template_input.value = self._get_default_output_template()
        self.profile_dd.value = "best"
        self.profile_hint.value = LM.get("profile_best_hint")
        self.update()

    def update_video_info(self, info: dict | None):
        """Updates the card based on fetched video info."""
        self.fetch_btn.disabled = False

        if info:
            self.time_start.disabled = False
            self.time_end.disabled = False

            # Determine Panel Type
            url = info.get("original_url", "") or info.get("webpage_url", "")

            # Simple heuristic
            if "youtube" in url or "youtu.be" in url:
                self.current_panel = YouTubePanel(info, lambda: None)
            elif "instagram" in url:
                self.current_panel = InstagramPanel(info, lambda: None)
            else:
                self.current_panel = GenericPanel(info, lambda: None)

            self.options_container.content = self.current_panel
        else:
            self.time_start.disabled = True
            self.time_end.disabled = True
            self.options_container.content = None
            self.current_panel = None

        self.update()

    def get_options(self) -> dict:
        """Collects all configured options."""
        cookies = self.cookies_dd.value if self.cookies_dd.value != "None" else None

        data = {
            "url": self.url_input.value,
            "start_time": self.time_start.value,
            "end_time": self.time_end.value,
            "cookies_from_browser": cookies,
            "force_generic": self.force_generic_cb.value,
            "download_profile": self.profile_dd.value or "best",
            "output_template": self.output_template_input.value
            or self._default_output_template,
        }

        if self.current_panel:
            data.update(self.current_panel.get_options())

        return data
