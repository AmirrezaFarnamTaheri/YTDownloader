"""
YouTube specific download panel.
"""

from typing import Any, Callable, Dict

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme
from views.components.panels.base_panel import BasePanel


class YouTubePanel(BasePanel):
    """
    Panel for YouTube downloads with advanced options.
    """

    def __init__(self, info: Dict[str, Any], on_option_change: Callable):
        super().__init__(info, on_option_change)

        # Initialize controls
        self.video_format_dd = ft.Dropdown(
            label=LM.get("format"),
            expand=True,
            on_change=lambda e: self.on_option_change(),
            **Theme.get_input_decoration(
                hint_text=LM.get("select_format"), prefix_icon=ft.icons.VIDEO_SETTINGS
            ),
        )

        self.audio_format_dd = ft.Dropdown(
            label=LM.get("audio_stream"),
            expand=True,
            visible=False,
            on_change=lambda e: self.on_option_change(),
            **Theme.get_input_decoration(
                hint_text=LM.get("select_audio"), prefix_icon=ft.icons.AUDIOTRACK
            ),
        )

        self.subtitle_dd = ft.Dropdown(
            label=LM.get("subtitles"),
            expand=True,
            options=[ft.dropdown.Option("None", LM.get("none"))],
            value="None",
            on_change=lambda e: self.on_option_change(),
            **Theme.get_input_decoration(
                hint_text=LM.get("select_subtitles"), prefix_icon=ft.icons.SUBTITLES
            ),
        )

        # Switches instead of Checkboxes for modern feel
        self.sponsorblock_cb = ft.Switch(
            label=LM.get("sponsorblock"),
            value=False,
            active_color=Theme.Primary.MAIN,
            on_change=lambda e: self.on_option_change(),
        )

        self.playlist_cb = ft.Switch(
            label=LM.get("playlist"),
            value=False,
            active_color=Theme.Primary.MAIN,
            on_change=lambda e: self.on_option_change(),
        )

        self.chapters_cb = ft.Switch(
            label=LM.get("split_chapters"),
            value=False,
            active_color=Theme.Primary.MAIN,
            on_change=lambda e: self.on_option_change(),
        )

        self.content = self.build()
        self._populate_options()

    def build(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        LM.get("youtube_options"),
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.Primary.MAIN,
                    ),
                    ft.Row([self.video_format_dd, self.audio_format_dd], spacing=15),
                    self.subtitle_dd,
                    ft.Divider(color=Theme.DIVIDER),
                    ft.Row(
                        [self.playlist_cb, self.sponsorblock_cb, self.chapters_cb],
                        wrap=True,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=15,
            ),
            **Theme.get_card_decoration(),
        )

    def _populate_options(self):
        # 1. Video Formats
        video_opts = []
        # Add 'best' default
        video_opts.append(ft.dropdown.Option("best", LM.get("best_quality")))

        if "video_streams" in self.info:
            for s in self.info["video_streams"]:
                fid = s.get("format_id")
                if not fid:
                    continue

                res = s.get("resolution", LM.get("status_unknown"))
                ext = s.get("ext", "")

                size_val = s.get("filesize")
                if size_val and isinstance(size_val, (int, float)):
                    size_str = f"{size_val / (1024 * 1024):.1f} MB"
                else:
                    size_str = s.get("filesize_str", "") or ""

                label = f"{res} ({ext}) {size_str}".strip()
                video_opts.append(ft.dropdown.Option(fid, label))

        self.video_format_dd.options = video_opts
        self.video_format_dd.value = "best"

        # 2. Audio Streams
        audio_opts = []
        if "audio_streams" in self.info and self.info["audio_streams"]:
            self.audio_format_dd.visible = True
            for s in self.info["audio_streams"]:
                abr = s.get("abr", "?")
                ext = s.get("ext", "")
                label = f"{abr}k ({ext})"
                audio_opts.append(ft.dropdown.Option(s.get("format_id"), label))
            self.audio_format_dd.options = audio_opts
            if audio_opts:
                self.audio_format_dd.value = audio_opts[0].key
        else:
            self.audio_format_dd.visible = False

        # 3. Subtitles
        sub_opts = [ft.dropdown.Option("None", LM.get("none"))]
        if "subtitles" in self.info:
            for lang, _ in self.info["subtitles"].items():
                sub_opts.append(ft.dropdown.Option(lang, lang))
        self.subtitle_dd.options = sub_opts
        self.subtitle_dd.value = "None"

        # 4. Playlist
        if self.info.get("_type") == "playlist" or "entries" in self.info:
            self.playlist_cb.value = True
            self.playlist_cb.disabled = False
        else:
            self.playlist_cb.value = False
            self.playlist_cb.disabled = True

    def get_options(self) -> Dict[str, Any]:
        return {
            "video_format": self.video_format_dd.value,
            "audio_format": (
                self.audio_format_dd.value if self.audio_format_dd.visible else None
            ),
            "subtitle_lang": (
                self.subtitle_dd.value if self.subtitle_dd.value != "None" else None
            ),
            "sponsorblock": self.sponsorblock_cb.value,
            "playlist": self.playlist_cb.value,
            "chapters": self.chapters_cb.value,
        }
