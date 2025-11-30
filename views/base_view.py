import flet as ft
from typing import Optional

from theme import Theme
from ui_utils import format_file_size


class BaseView(ft.Container):
    def __init__(self, title: str, icon: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.expand = True
        self.padding = 30
        self.bgcolor = Theme.BG_DARK
        self.content_col = ft.Column(expand=True, spacing=20)

        self.header = ft.Row(
            [
                ft.Icon(icon, size=32, color=Theme.PRIMARY) if icon else ft.Container(),
                ft.Text(
                    title, size=28, weight=ft.FontWeight.BOLD, color=Theme.TEXT_PRIMARY
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=15,
        )

        self.content_col.controls.append(self.header)
        self.content_col.controls.append(ft.Divider(color=Theme.BORDER))
        self.content = self.content_col

    def add_control(self, control):
        self.content_col.controls.append(control)
