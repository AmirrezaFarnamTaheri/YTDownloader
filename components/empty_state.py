import flet as ft

from theme import Theme


class EmptyState(ft.Container):
    def __init__(self, icon: str, message: str):
        super().__init__()
        self.expand = True
        self.alignment = ft.alignment.center
        self.content = ft.Column(
            [
                ft.Icon(icon, size=64, color=Theme.TEXT_MUTED),
                ft.Text(message, size=18, color=Theme.TEXT_MUTED),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )
