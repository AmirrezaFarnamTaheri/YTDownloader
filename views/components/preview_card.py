import flet as ft
from theme import Theme

class DownloadPreviewCard(ft.Container):
    def __init__(self, thumbnail_img):
        super().__init__()
        self.thumbnail_img = thumbnail_img

        self.padding = 0
        self.bgcolor = ft.Colors.BLACK
        self.border_radius = 12
        self.alignment = ft.alignment.center
        self.shadow = ft.BoxShadow(blur_radius=15, color=ft.Colors.BLACK54)

        self.content = self.thumbnail_img
