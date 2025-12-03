"""
YouTube specific download panel.
"""

from typing import Any, Callable, Dict, List

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
            **Theme.get_input_decoration(hint_text="Select Format"),
        )

        self.audio_format_dd = ft.Dropdown(
            label=LM.get("audio_stream"),
            expand=True,
            visible=False,
            **Theme.get_input_decoration(hint_text="Select Audio"),
        )

        self.subtitle_dd = ft.Dropdown(
            label=LM.get("subtitles"),
            expand=True,
            options=[ft.dropdown.Option("None", "None")],
            value="None",
            **Theme.get_input_decoration(hint_text="Select Subtitles"),
        )

        self.sponsorblock_cb = ft.Checkbox(
            label=LM.get("sponsorblock"),
            value=False,
            fill_color=Theme.Primary.MAIN,
        )

        self.playlist_cb = ft.Checkbox(
            label=LM.get("playlist"),
            value=False,
            fill_color=Theme.Primary.MAIN,
        )

        self.chapters_cb = ft.Checkbox(
            label="Split by Chapters", # TODO: Add to locale
            value=False,
            fill_color=Theme.Primary.MAIN,
        )

        self.content = self.build()
        self._populate_options()

    def build(self):
        return ft.Column(
            [
                ft.Text("YouTube Options", weight=ft.FontWeight.BOLD, color=Theme.Primary.MAIN),
                ft.Row([self.video_format_dd, self.audio_format_dd], spacing=10),
                self.subtitle_dd,
                ft.Row([self.playlist_cb, self.sponsorblock_cb, self.chapters_cb], wrap=True),
            ],
            spacing=10,
        )

    def _populate_options(self):
        # 1. Video Formats
        video_opts = []
        # Add 'best' default
        video_opts.append(ft.dropdown.Option("best", LM.get("best_quality")))

        if "video_streams" in self.info:
            for s in self.info["video_streams"]:
                # Simple label
                res = s.get('resolution', 'Unknown')
                ext = s.get('ext', '')
                size = s.get('filesize_str', '') or s.get('filesize', '')
                if size and isinstance(size, int):
                    size = f"{size / 1024 / 1024:.1f}MB"

                label = f"{res} ({ext}) {size}"
                video_opts.append(ft.dropdown.Option(s.get("format_id"), label))

        self.video_format_dd.options = video_opts
        self.video_format_dd.value = "best"

        # 2. Audio Streams
        audio_opts = []
        if "audio_streams" in self.info and self.info["audio_streams"]:
            self.audio_format_dd.visible = True
            for s in self.info["audio_streams"]:
                abr = s.get('abr', '?')
                ext = s.get('ext', '')
                label = f"{abr}k ({ext})"
                audio_opts.append(ft.dropdown.Option(s.get("format_id"), label))
            self.audio_format_dd.options = audio_opts
            if audio_opts:
                self.audio_format_dd.value = audio_opts[0].key
        else:
            self.audio_format_dd.visible = False

        # 3. Subtitles
        sub_opts = [ft.dropdown.Option("None", "None")]
        if "subtitles" in self.info:
            for lang, formats in self.info["subtitles"].items():
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
            "audio_format": self.audio_format_dd.value if self.audio_format_dd.visible else None,
            "subtitle_lang": self.subtitle_dd.value if self.subtitle_dd.value != "None" else None,
            "sponsorblock": self.sponsorblock_cb.value,
            "playlist": self.playlist_cb.value,
            "chapters": self.chapters_cb.value,
        }
