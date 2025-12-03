import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme


class DownloadInputCard(ft.Container):
    def __init__(
        self,
        url_input,
        fetch_btn,
        video_format_dd,
        cookies_dd,
        playlist_cb,
        sponsorblock_cb,
        force_generic_cb,
        time_start,
        time_end,
    ):
        super().__init__()
        self.url_input = url_input
        self.fetch_btn = fetch_btn
        self.video_format_dd = video_format_dd
        self.cookies_dd = cookies_dd
        self.playlist_cb = playlist_cb
        self.sponsorblock_cb = sponsorblock_cb
        self.force_generic_cb = force_generic_cb
        self.time_start = time_start
        self.time_end = time_end

        self.padding = 20
        self.bgcolor = Theme.BG_CARD
        self.border_radius = 16
        self.border = ft.border.all(1, Theme.BORDER)

        self.content = self._build_content()

    def _build_content(self):
        # Platform Icons - Wrap on small screens
        platform_icons = ft.Row(
            [
                ft.Icon(
                    ft.Icons.ONDEMAND_VIDEO, color=ft.Colors.RED_400, tooltip="YouTube"
                ),
                ft.Icon(
                    ft.Icons.TELEGRAM, color=ft.Colors.BLUE_400, tooltip="Telegram"
                ),
                ft.Icon(
                    ft.Icons.ALTERNATE_EMAIL,
                    color=ft.Colors.LIGHT_BLUE_400,
                    tooltip="Twitter/X",
                ),
                ft.Icon(
                    ft.Icons.CAMERA_ALT, color=ft.Colors.PINK_400, tooltip="Instagram"
                ),
                ft.Icon(ft.Icons.LINK, color=Theme.TEXT_MUTED, tooltip="Generic Files"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            opacity=0.7,
            wrap=True,
        )

        # Options Row - Use wrap for responsiveness
        options_row = ft.Row(
            [
                self.video_format_dd,
                self.cookies_dd,
            ],
            wrap=True,
            spacing=10,
            run_spacing=10,
            alignment=ft.MainAxisAlignment.START,
        )

        checkboxes_row = ft.Row(
            [
                self.playlist_cb,
                self.sponsorblock_cb,
                self.force_generic_cb,
            ],
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
            spacing=20,
            run_spacing=10,
        )

        time_row = ft.Row(
            [
                ft.Text(LM.get("time_range_label"), color=Theme.TEXT_MUTED),
                self.time_start,
                ft.Text("-"),
                self.time_end,
            ],
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
            spacing=5,
            run_spacing=5,
        )

        # Main Input Row (URL + Button)
        input_row = ft.Row(
            [ft.Container(self.url_input, expand=True), self.fetch_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=False,  # We want these side-by-side if possible, but URL expands
        )

        return ft.Column(
            [
                platform_icons,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                input_row,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                options_row,
                checkboxes_row,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                time_row,
            ]
        )
