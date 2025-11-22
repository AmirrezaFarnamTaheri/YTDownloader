import flet as ft
from theme import Theme
from .base_view import BaseView
from ui_utils import format_file_size, open_folder
from views.components.input_card import DownloadInputCard
from views.components.preview_card import DownloadPreviewCard
import logging
import os


class DownloadView(BaseView):
    def __init__(
        self, on_fetch_info, on_add_to_queue, on_batch_import, on_schedule, state
    ):
        super().__init__("New Download", ft.Icons.DOWNLOAD)
        self.on_fetch_info = on_fetch_info
        self.on_add_to_queue = on_add_to_queue
        self.on_batch_import = on_batch_import
        self.on_schedule = on_schedule
        self.state = state

        # --- Header Actions ---
        self.open_folder_btn = ft.IconButton(
            ft.Icons.FOLDER_OPEN,
            tooltip="Open Downloads Folder",
            on_click=self.open_download_folder,
            icon_color=Theme.PRIMARY,
        )

        self.batch_btn = ft.IconButton(
            ft.Icons.FILE_UPLOAD,
            tooltip="Batch Import URLs",
            on_click=lambda e: self.on_batch_import(),
            icon_color=Theme.ACCENT,
        )

        self.schedule_btn = ft.IconButton(
            ft.Icons.SCHEDULE,
            tooltip="Schedule Download",
            on_click=lambda e: self.on_schedule(e),
            icon_color=Theme.ACCENT,
        )

        self.header.controls.extend([
            ft.Container(expand=True),
            self.schedule_btn,
            self.batch_btn,
            self.open_folder_btn
        ])

        # --- Input Components ---
        self.url_input = ft.TextField(
            label="Video URL",
            hint_text="Paste YouTube, Telegram, Twitter link here...",
            expand=True,
            border_color=Theme.BORDER,
            focused_border_color=Theme.PRIMARY,
            prefix_icon=ft.Icons.LINK,
            text_size=16,
            bgcolor=Theme.BG_INPUT,
            border_radius=12,
            on_submit=lambda e: on_fetch_info(self.url_input.value),
        )

        self.fetch_btn = ft.IconButton(
            ft.Icons.SEARCH,
            on_click=lambda e: on_fetch_info(self.url_input.value),
            tooltip="Fetch Metadata",
            icon_color=Theme.PRIMARY,
            style=ft.ButtonStyle(
                bgcolor=Theme.BG_HOVER,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=10,
            ),
        )

        self.cookies_dd = ft.Dropdown(
            label="Browser Cookies",
            options=[
                ft.dropdown.Option("None"),
                ft.dropdown.Option("chrome"),
                ft.dropdown.Option("firefox"),
                ft.dropdown.Option("opera"),
                ft.dropdown.Option("edge"),
                ft.dropdown.Option("brave"),
                ft.dropdown.Option("vivaldi"),
                ft.dropdown.Option("safari"),
            ],
            value="None",
            width=180,
            border_color=Theme.BORDER,
            border_radius=12,
            bgcolor=Theme.BG_INPUT,
            tooltip="Use cookies from browser to bypass login/age restrictions",
            text_size=14,
            dense=True,
        )

        # --- Preview Components ---
        self.thumbnail_img = ft.Image(
            src="",
            width=320,
            height=180,
            fit=ft.ImageFit.COVER,
            border_radius=12,
            visible=False,
            opacity=0,
            animate_opacity=300,
        )

        self.title_text = ft.Text(
            "Ready to download",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=Theme.TEXT_PRIMARY,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self.duration_text = ft.Text("Paste a URL to begin", color=Theme.TEXT_SECONDARY)

        # --- Options Components ---
        self.video_format_dd = ft.Dropdown(
            label="Video Quality",
            options=[],
            expand=True,
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_INPUT,
            dense=True,
        )
        self.audio_format_dd = ft.Dropdown(
            label="Audio Format",
            options=[],
            expand=True,
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_INPUT,
            dense=True,
        )

        self.playlist_cb = ft.Checkbox(label="Playlist", fill_color=Theme.PRIMARY)
        self.sponsorblock_cb = ft.Checkbox(label="SponsorBlock", fill_color=Theme.PRIMARY)
        self.force_generic_cb = ft.Checkbox(
            label="Force Generic",
            fill_color=Theme.WARNING,
            tooltip="Bypass yt-dlp extraction"
        )

        self.subtitle_dd = ft.Dropdown(
            label="Subtitles",
            options=[
                ft.dropdown.Option("None"),
                ft.dropdown.Option("en"),
                ft.dropdown.Option("es"),
                ft.dropdown.Option("jp"),
            ],
            value="None",
            width=150,
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_INPUT,
            dense=True,
        )

        self.time_start = ft.TextField(
            label="Start Time",
            width=120,
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_INPUT,
            hint_text="00:00:00",
            dense=True,
        )
        self.time_end = ft.TextField(
            label="End Time",
            width=120,
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_INPUT,
            hint_text="00:00:00",
            dense=True,
        )

        # Advanced Options
        self.advanced_options = ft.ExpansionTile(
            title=ft.Text("Advanced Options", color=Theme.TEXT_SECONDARY),
            icon_color=Theme.PRIMARY,
            controls=[
                ft.Container(
                    padding=10,
                    content=ft.Column([
                        ft.Row([self.subtitle_dd, self.time_start, self.time_end], wrap=True),
                        ft.Row([self.playlist_cb, self.sponsorblock_cb, self.force_generic_cb], wrap=True),
                    ])
                )
            ]
        )

        self.download_btn = ft.ElevatedButton(
            "Add to Queue",
            icon=ft.Icons.ADD_CIRCLE,
            bgcolor=Theme.PRIMARY,
            color=Theme.BG_DARK,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=20,
                elevation=5,
            ),
            on_click=lambda e: self._on_add_click(e),
            width=200,
        )

        self.build_layout()

    def build_layout(self):
        input_card = DownloadInputCard(
            self.on_fetch_info,
            self.url_input,
            self.fetch_btn,
            self.cookies_dd
        )

        preview_card = DownloadPreviewCard(self.thumbnail_img)

        details_col = ft.Column(
            [
                self.title_text,
                self.duration_text,
                ft.Divider(height=20, color=Theme.BORDER),
                ft.Text("Quality Selection", weight=ft.FontWeight.W_600, color=Theme.TEXT_PRIMARY),
                ft.Row([self.video_format_dd, self.audio_format_dd]),
                self.advanced_options,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Row([self.download_btn], alignment=ft.MainAxisAlignment.END),
            ],
            expand=True,
        )

        main_content = ft.ResponsiveRow(
            [
                ft.Column([preview_card], col={"sm": 12, "md": 5}),
                ft.Column([details_col], col={"sm": 12, "md": 7}),
            ],
            spacing=30,
        )

        self.add_control(input_card)
        self.add_control(ft.Divider(height=30, color=ft.Colors.TRANSPARENT))
        self.add_control(ft.Container(content=main_content, padding=10))

    def update_info(self, info):
        if not info:
            return

        self.thumbnail_img.src = info.get("thumbnail") or ""
        self.thumbnail_img.visible = True
        self.thumbnail_img.opacity = 1

        self.title_text.value = info.get("title", "N/A")
        self.duration_text.value = f"Duration: {info.get('duration', 'N/A')}"

        # Video Options
        video_opts = []
        for s in info.get("video_streams", []):
            label = f"{s.get('resolution', 'N/A')} ({s.get('ext', '?')})"
            if s.get("filesize"):
                label += f" - {format_file_size(s['filesize'])}"
            video_opts.append(ft.dropdown.Option(key=s["format_id"], text=label))

        if not video_opts:
            video_opts = [ft.dropdown.Option(key="best", text="Best / Direct")]

        self.video_format_dd.options = video_opts
        self.video_format_dd.value = video_opts[0].key

        # Audio Options
        audio_opts = [
            ft.dropdown.Option(
                key=s["format_id"],
                text=f"{s.get('abr', 'N/A')}kbps ({s.get('ext', '?')})",
            )
            for s in info.get("audio_streams", [])
        ]
        self.audio_format_dd.options = audio_opts
        self.audio_format_dd.value = audio_opts[0].key if audio_opts else None
        self.audio_format_dd.disabled = not audio_opts

        self.update()

    def _on_add_click(self, e):
        # Handle cookie selection
        cookies = self.cookies_dd.value if self.cookies_dd.value != "None" else None

        data = {
            "url": self.url_input.value,
            "video_format": self.video_format_dd.value,
            "playlist": self.playlist_cb.value,
            "sponsorblock": self.sponsorblock_cb.value,
            "force_generic": self.force_generic_cb.value,
            "start_time": self.time_start.value,
            "end_time": self.time_end.value,
            "output_template": "%(title)s.%(ext)s",
            "cookies_from_browser": cookies,
        }
        self.on_add_to_queue(data)

    def open_download_folder(self, e):
        path = os.path.expanduser("~/Downloads")
        try:
            open_folder(path)
        except Exception as ex:
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text(f"Failed to open folder: {ex}"))
                )
