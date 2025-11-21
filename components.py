import flet as ft
from typing import Dict, Any

class DownloadItemControl:
    def __init__(self, item: Dict[str, Any], on_cancel: Any, on_remove: Any, on_reorder: Any, is_selected: bool = False):
        self.item = item
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.is_selected = is_selected

        self.progress_bar = ft.ProgressBar(value=0, height=6, border_radius=3, color=ft.Colors.BLUE_ACCENT_400, bgcolor=ft.Colors.GREY_800)

        self.status_text = ft.Text(item['status'], size=11, color=ft.Colors.GREY_400, weight=ft.FontWeight.W_600)
        self.details_text = ft.Text("Waiting...", size=11, color=ft.Colors.GREY_500, font_family="Roboto Mono")

        self.title_text = ft.Text(
            self.item.get('title', self.item['url']),
            weight=ft.FontWeight.W_600,
            size=15,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=ft.Colors.WHITE,
            max_lines=1
        )

        self.icon = self._get_icon_for_item()
        self.view = self.build()

    def _get_icon_for_item(self):
        url = self.item.get('url', '').lower()
        if "youtube" in url or "youtu.be" in url:
            return ft.Icon(ft.Icons.SMART_DISPLAY, size=28, color=ft.Colors.RED_400)
        elif "t.me" in url or "telegram" in url:
            return ft.Icon(ft.Icons.TELEGRAM, size=28, color=ft.Colors.BLUE_400)
        elif "twitter" in url or "x.com" in url:
            return ft.Icon(ft.Icons.ALTERNATE_EMAIL, size=28, color=ft.Colors.WHITE)
        elif "instagram" in url:
            return ft.Icon(ft.Icons.CAMERA_ALT, size=28, color=ft.Colors.PINK_400)
        else:
            return ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=28, color=ft.Colors.BLUE_GREY_200)

    def build(self):
        # Modern Card Design with "Glassmorphism" feel
        bg_color = ft.Colors.GREY_900 if not self.is_selected else ft.Colors.with_opacity(0.1, ft.Colors.BLUE_400)
        border_color = ft.Colors.GREY_800 if not self.is_selected else ft.Colors.BLUE_400

        return ft.Container(
            content=ft.Row([
                # Icon Container
                ft.Container(
                    content=self.icon,
                    width=50, height=50,
                    bgcolor=ft.Colors.BLACK45,
                    border_radius=12,
                    alignment=ft.alignment.center,
                    border=ft.border.all(1, ft.Colors.GREY_800)
                ),
                # Info Column
                ft.Column([
                    ft.Row([self.title_text], alignment=ft.MainAxisAlignment.START),
                    self.progress_bar,
                    ft.Row([
                        self.status_text,
                        ft.Container(expand=True),
                        self.details_text
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=6, expand=True),

                # Actions
                ft.Row([
                    ft.Column([
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP, on_click=lambda e: self.on_reorder(self.item, -1), icon_size=18, tooltip="Move Up", style=ft.ButtonStyle(padding=0, shape=ft.CircleBorder())),
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, on_click=lambda e: self.on_reorder(self.item, 1), icon_size=18, tooltip="Move Down", style=ft.ButtonStyle(padding=0, shape=ft.CircleBorder())),
                    ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),

                    ft.IconButton(ft.Icons.STOP_CIRCLE_OUTLINED, on_click=lambda e: self.on_cancel(self.item), icon_size=24, tooltip="Cancel", icon_color=ft.Colors.RED_300),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=lambda e: self.on_remove(self.item), icon_size=24, tooltip="Remove", icon_color=ft.Colors.GREY_500),
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)

            ], spacing=12),
            padding=12,
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=16,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._on_hover
        )

    def _on_hover(self, e):
        e.control.bgcolor = ft.Colors.GREY_800 if e.data == "true" and not self.is_selected else (ft.Colors.GREY_900 if not self.is_selected else ft.Colors.with_opacity(0.1, ft.Colors.BLUE_400))
        e.control.update()

    def update_progress(self):
        self.status_text.value = self.item['status']
        status_color = ft.Colors.GREY_400

        if self.item['status'] == 'Downloading':
            status_color = ft.Colors.BLUE_400
        elif self.item['status'] == 'Completed':
            status_color = ft.Colors.GREEN_400
        elif self.item['status'] == 'Error':
            status_color = ft.Colors.RED_400

        self.status_text.color = status_color

        if 'speed' in self.item:
             self.details_text.value = f"{self.item.get('size', '')}  •  {self.item.get('speed', '')}  •  ETA: {self.item.get('eta', '')}"
        else:
             self.details_text.value = ""

        self.status_text.update()
        self.details_text.update()
        self.progress_bar.update()
        self.title_text.value = self.item.get('title', self.item['url'])
        self.title_text.update()
