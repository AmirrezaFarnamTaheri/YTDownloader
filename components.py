import flet as ft
from typing import Dict, Any
from theme import Theme

class DownloadItemControl:
    def __init__(self, item: Dict[str, Any], on_cancel: Any, on_remove: Any, on_reorder: Any, is_selected: bool = False):
        self.item = item
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.is_selected = is_selected

        self.progress_bar = ft.ProgressBar(
            value=0,
            height=6,
            border_radius=3,
            color=Theme.PRIMARY,
            bgcolor=Theme.BG_DARK
        )

        self.status_text = ft.Text(item['status'], size=12, color=Theme.TEXT_SECONDARY)
        self.details_text = ft.Text("Waiting...", size=12, color=Theme.TEXT_SECONDARY)
        self.title_text = ft.Text(
            self.item.get('title', self.item['url']),
            weight=ft.FontWeight.W_600,
            size=15,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=Theme.TEXT_PRIMARY,
            max_lines=1
        )

        self.view = self.build()

    def build(self):
        bg_color = Theme.BG_CARD if not self.is_selected else ft.Colors.with_opacity(0.1, Theme.PRIMARY)
        border_color = Theme.BORDER if not self.is_selected else Theme.PRIMARY

        icon = ft.Icons.VIDEO_FILE
        if self.item.get('is_audio'): icon = ft.Icons.AUDIO_FILE
        elif self.item.get('is_playlist'): icon = ft.Icons.PLAYLIST_PLAY

        return ft.Container(
            content=ft.Row([
                # Thumbnail/Icon
                ft.Container(
                    content=ft.Icon(icon, size=24, color=Theme.TEXT_SECONDARY),
                    width=48, height=48, bgcolor=Theme.BG_DARK, border_radius=8,
                    alignment=ft.alignment.center
                ),

                # Info Column
                ft.Column([
                    ft.Row([
                        self.title_text,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.progress_bar,
                    ft.Row([
                        self.status_text,
                        self.details_text
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=6, expand=True),

                # Actions
                ft.Row([
                    ft.Column([
                        ft.IconButton(
                            ft.Icons.KEYBOARD_ARROW_UP,
                            on_click=lambda e: self.on_reorder(self.item, -1),
                            icon_size=18,
                            tooltip="Move Up",
                            style=ft.ButtonStyle(padding=0),
                            icon_color=Theme.TEXT_SECONDARY
                        ),
                        ft.IconButton(
                            ft.Icons.KEYBOARD_ARROW_DOWN,
                            on_click=lambda e: self.on_reorder(self.item, 1),
                            icon_size=18,
                            tooltip="Move Down",
                            style=ft.ButtonStyle(padding=0),
                            icon_color=Theme.TEXT_SECONDARY
                        ),
                    ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),

                    ft.IconButton(
                        ft.Icons.CANCEL,
                        on_click=lambda e: self.on_cancel(self.item),
                        icon_size=20,
                        tooltip="Cancel",
                        icon_color=Theme.ERROR
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE,
                        on_click=lambda e: self.on_remove(self.item),
                        icon_size=20,
                        tooltip="Remove",
                        icon_color=Theme.TEXT_SECONDARY
                    ),
                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER)

            ], spacing=12),
            padding=12,
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=12,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
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
