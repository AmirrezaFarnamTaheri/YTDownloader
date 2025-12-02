import flet as ft

from theme import Theme


class DownloadPreviewCard(ft.Container):
    def __init__(self):
        super().__init__()
        self.visible = False
        self.padding = 15
        self.bgcolor = Theme.BG_CARD
        self.border_radius = 12
        self.border = ft.border.all(1, Theme.BORDER)

        self.thumbnail = ft.Image(
            src="",
            width=240,
            height=135,
            fit=ft.ImageFit.COVER,
            border_radius=8,
        )

        self.title_text = ft.Text(
            "Video Title",
            size=16,
            weight=ft.FontWeight.BOLD,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self.duration_text = ft.Text("00:00", size=12, color=Theme.TEXT_MUTED)
        self.author_text = ft.Text("Channel", size=12, color=Theme.TEXT_MUTED)

        self.content = ft.Row(
            [
                self.thumbnail,
                ft.Container(width=15),
                ft.Column(
                    [
                        self.title_text,
                        ft.Container(height=5),
                        self.author_text,
                        self.duration_text,
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def update_info(self, info: dict):
        if not info:
            self.visible = False
            self.update()
            return

        self.title_text.value = info.get("title", "Unknown Title")
        self.thumbnail.src = info.get("thumbnail", "")
        duration = info.get("duration_string") or info.get("duration")
        self.duration_text.value = str(duration) if duration else ""
        self.author_text.value = info.get("uploader", "Unknown Channel")

        self.visible = True
        self.update()
