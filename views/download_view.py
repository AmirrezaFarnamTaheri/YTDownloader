import flet as ft
from theme import Theme
from .base_view import BaseView
from ui_utils import format_file_size, validate_url

class DownloadView(BaseView):
    def __init__(self,
                 on_fetch_info,
                 on_add_to_queue,
                 on_batch_import,
                 on_schedule,
                 state):
        super().__init__("New Download", ft.Icons.DOWNLOAD)
        self.on_fetch_info = on_fetch_info
        self.on_add_to_queue = on_add_to_queue
        self.state = state

        # Platform Icons
        self.platform_icons = ft.Row([
            ft.Icon(ft.Icons.ONDEMAND_VIDEO, color=ft.Colors.RED_400, tooltip="YouTube"),
            ft.Icon(ft.Icons.TELEGRAM, color=ft.Colors.BLUE_400, tooltip="Telegram"),
            ft.Icon(ft.Icons.ALTERNATE_EMAIL, color=ft.Colors.LIGHT_BLUE_400, tooltip="Twitter/X"),
            ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.PINK_400, tooltip="Instagram"),
            ft.Icon(ft.Icons.LINK, color=ft.Colors.GREY_400, tooltip="Generic Files"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)

        # Inputs
        self.url_input = ft.TextField(
            label="URL",
            hint_text="Paste link here...",
            expand=True,
            border_color=Theme.BORDER,
            focused_border_color=Theme.PRIMARY,
            prefix_icon=ft.Icons.LINK,
            text_size=16,
            bgcolor=Theme.BG_CARD,
            border_radius=10,
            on_submit=lambda e: on_fetch_info(self.url_input.value)
        )

        self.fetch_btn = ft.IconButton(
            ft.Icons.SEARCH,
            on_click=lambda e: on_fetch_info(self.url_input.value),
            tooltip="Fetch Info",
            icon_color=Theme.PRIMARY,
            icon_size=30
        )

        # Preview Area
        self.thumbnail_img = ft.Image(src="", width=320, height=180, fit=ft.ImageFit.COVER, border_radius=10, visible=False)
        self.title_text = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color=Theme.TEXT_PRIMARY)
        self.duration_text = ft.Text("", color=Theme.TEXT_SECONDARY)

        # Options
        self.video_format_dd = ft.Dropdown(label="Video Quality", options=[], expand=True, border_color=Theme.BORDER, border_radius=8, bgcolor=Theme.BG_CARD)
        self.audio_format_dd = ft.Dropdown(label="Audio Format", options=[], expand=True, border_color=Theme.BORDER, border_radius=8, bgcolor=Theme.BG_CARD)

        self.playlist_cb = ft.Checkbox(label="Playlist", fill_color=Theme.PRIMARY)
        self.sponsorblock_cb = ft.Checkbox(label="SponsorBlock", fill_color=Theme.PRIMARY)
        self.force_generic_cb = ft.Checkbox(label="Force Generic", fill_color=Theme.WARNING, tooltip="Bypass extraction")

        self.subtitle_dd = ft.Dropdown(
            label="Subtitles",
            options=[ft.dropdown.Option("None"), ft.dropdown.Option("en"), ft.dropdown.Option("es")],
            value="None",
            width=150,
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD
        )

        self.time_start = ft.TextField(label="Start", width=120, border_color=Theme.BORDER, border_radius=8, bgcolor=Theme.BG_CARD, hint_text="HH:MM:SS")
        self.time_end = ft.TextField(label="End", width=120, border_color=Theme.BORDER, border_radius=8, bgcolor=Theme.BG_CARD, hint_text="HH:MM:SS")

        self.download_btn = ft.ElevatedButton(
            "Add to Queue",
            icon=ft.Icons.ADD,
            bgcolor=Theme.PRIMARY,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=20,
                elevation=5,
            ),
            on_click=lambda e: self._on_add_click(e)
        )

        self.build_layout()

    def build_layout(self):
        input_row = ft.Row([self.url_input, self.fetch_btn], alignment=ft.MainAxisAlignment.CENTER)

        preview_col = ft.Column([
             ft.Container(
                 content=ft.Stack([
                     ft.Container(bgcolor=ft.Colors.BLACK54, width=320, height=180, border_radius=10),
                     self.thumbnail_img
                 ]),
                 border_radius=12,
                 border=ft.border.all(1, Theme.BORDER),
                 shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK)
             ),
             self.title_text,
             self.duration_text
        ], alignment=ft.MainAxisAlignment.START)

        options_col = ft.Container(
            padding=20,
            bgcolor=Theme.BG_CARD,
            border_radius=12,
            content=ft.Column([
                ft.Text("Options", size=16, weight=ft.FontWeight.W_600, color=Theme.TEXT_PRIMARY),
                ft.Row([self.video_format_dd, self.audio_format_dd]),
                ft.Divider(height=10, color=Theme.BORDER),
                ft.Row([self.playlist_cb, self.sponsorblock_cb, self.force_generic_cb], wrap=True),
                ft.Row([self.subtitle_dd, self.time_start, self.time_end], wrap=True),
            ])
        )

        main_content = ft.Row([
            preview_col,
            ft.Container(width=20),
            ft.Column([
                options_col,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Row([self.download_btn], alignment=ft.MainAxisAlignment.END)
            ], expand=True)
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)

        self.add_control(self.platform_icons)
        self.add_control(ft.Divider(color=ft.Colors.TRANSPARENT, height=10))
        self.add_control(input_row)
        self.add_control(ft.Divider(height=20, color=Theme.BORDER))
        self.add_control(ft.Container(content=main_content, padding=10))

    def update_info(self, info):
        if not info: return
        self.thumbnail_img.src = info.get('thumbnail') or ""
        self.thumbnail_img.visible = True
        self.title_text.value = info.get('title', 'N/A')
        self.duration_text.value = info.get('duration', '')

        # Video Options
        video_opts = []
        for s in info.get('video_streams', []):
            label = f"{s.get('resolution', 'N/A')} ({s.get('ext', '?')})"
            if s.get('filesize'): label += f" - {format_file_size(s['filesize'])}"
            video_opts.append(ft.dropdown.Option(key=s['format_id'], text=label))

        if not video_opts:
             video_opts = [ft.dropdown.Option(key="best", text="Best / Direct")]

        self.video_format_dd.options = video_opts
        self.video_format_dd.value = video_opts[0].key

        # Audio Options
        audio_opts = [ft.dropdown.Option(key=s['format_id'], text=f"{s.get('abr', 'N/A')}kbps ({s.get('ext', '?')})") for s in info.get('audio_streams', [])]
        self.audio_format_dd.options = audio_opts
        self.audio_format_dd.value = audio_opts[0].key if audio_opts else None
        self.audio_format_dd.disabled = not audio_opts

        self.update()

    def _on_add_click(self, e):
        data = {
            "url": self.url_input.value,
            "video_format": self.video_format_dd.value,
            "playlist": self.playlist_cb.value,
            "sponsorblock": self.sponsorblock_cb.value,
            "force_generic": self.force_generic_cb.value,
            "start_time": self.time_start.value,
            "end_time": self.time_end.value,
            "output_template": "%(title)s.%(ext)s" # Default for now, could be fetched from config
        }
        self.on_add_to_queue(data)
