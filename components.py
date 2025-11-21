import flet as ft
from typing import Dict, Any

class DownloadItemControl:
    def __init__(self, item: Dict[str, Any], on_cancel: Any, on_remove: Any, on_reorder: Any, is_selected: bool = False):
        self.item = item
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.is_selected = is_selected

        self.progress_bar = ft.ProgressBar(value=0, height=8, border_radius=4, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.GREY_800)
        self.status_text = ft.Text(item['status'], size=12, color=ft.Colors.GREY_400)
        self.details_text = ft.Text("Waiting...", size=12, color=ft.Colors.GREY_500)
        self.title_text = ft.Text(
            self.item.get('title', self.item['url']),
            weight=ft.FontWeight.BOLD,
            size=16,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=ft.Colors.WHITE,
            max_lines=1
        )

        self.view = self.build()

    def build(self):
        # Modern Card Design
        bg_color = ft.Colors.GREY_900 if not self.is_selected else ft.Colors.BLUE_GREY_900
        border_color = ft.Colors.TRANSPARENT if not self.is_selected else ft.Colors.BLUE_400

        return ft.Container(
            content=ft.Row([
                # Thumbnail or Icon placeholder
                ft.Container(
                    content=ft.Icon(ft.Icons.VIDEO_FILE, size=32, color=ft.Colors.BLUE_200),
                    width=60, height=60, bgcolor=ft.Colors.BLACK26, border_radius=8,
                    alignment=ft.alignment.center
                ),
                # Info Column - using expand=True instead of ft.Expanded
                ft.Column([
                    self.title_text,
                    self.progress_bar,
                    ft.Row([
                        self.status_text,
                        self.details_text
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=8, expand=True),

                # Actions
                ft.Row([
                    ft.Column([
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP, on_click=lambda e: self.on_reorder(self.item, -1), icon_size=20, tooltip="Move Up", style=ft.ButtonStyle(padding=0)),
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, on_click=lambda e: self.on_reorder(self.item, 1), icon_size=20, tooltip="Move Down", style=ft.ButtonStyle(padding=0)),
                    ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),

                    ft.IconButton(ft.Icons.CANCEL, on_click=lambda e: self.on_cancel(self.item), icon_size=20, tooltip="Cancel", icon_color=ft.Colors.RED_400),
                    ft.IconButton(ft.Icons.DELETE, on_click=lambda e: self.on_remove(self.item), icon_size=20, tooltip="Remove", icon_color=ft.Colors.GREY_400),
                ], spacing=5, alignment=ft.MainAxisAlignment.CENTER)

            ], spacing=15),
            padding=15,
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=12,
            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.Colors.BLACK12,
                offset=ft.Offset(0, 2),
            )
        )

    def update_progress(self):
        self.status_text.value = self.item['status']
        if 'speed' in self.item:
             self.details_text.value = f"{self.item.get('size', '')} • {self.item.get('speed', '')} • ETA: {self.item.get('eta', '')}"
        else:
             self.details_text.value = ""

        self.status_text.update()
        self.details_text.update()
        self.progress_bar.update()
        self.title_text.value = self.item.get('title', self.item['url'])
        self.title_text.update()
