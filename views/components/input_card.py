import flet as ft
from theme import Theme


class DownloadInputCard(ft.Container):
    def __init__(self, on_fetch_info, url_input, fetch_btn, cookies_dd):
        super().__init__()
        self.on_fetch_info = on_fetch_info
        self.url_input = url_input
        self.fetch_btn = fetch_btn
        self.cookies_dd = cookies_dd

        self.padding = 20
        self.bgcolor = Theme.BG_CARD
        self.border_radius = 16
        self.border = ft.border.all(1, Theme.BORDER)

        self.content = self._build_content()

    def _build_content(self):
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
        )

        return ft.Column(
            [
                platform_icons,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Row(
                    [self.url_input, self.fetch_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row([self.cookies_dd], alignment=ft.MainAxisAlignment.END),
            ]
        )
