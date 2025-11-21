import flet as ft
from typing import Dict, Any
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

class DownloadItemControl:
    def __init__(
        self,
        item: Dict[str, Any],
        on_cancel: Any,
        on_remove: Any,
        on_reorder: Any,
        on_retry: Any = None,
        is_selected: bool = False,
    ):
        self.item = item
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.on_retry = on_retry
        self.is_selected = is_selected

        self.progress_bar = ft.ProgressBar(
            value=0,
            height=6,
            border_radius=3,
            color=Theme.PRIMARY,
            bgcolor=Theme.BG_DARK,
        )

        self.status_text = ft.Text(item["status"], size=12, color=Theme.TEXT_SECONDARY)
        self.details_text = ft.Text("Waiting...", size=12, color=Theme.TEXT_SECONDARY)
        self.title_text = ft.Text(
            self.item.get("title", self.item["url"]),
            weight=ft.FontWeight.W_600,
            size=15,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=Theme.TEXT_PRIMARY,
            max_lines=1,
        )

        self.icon = self._get_icon_for_item()
        self.actions_row = ft.Row(spacing=0, alignment=ft.MainAxisAlignment.CENTER)
        self._update_actions()
        self.view = self.build()

    def _get_icon_for_item(self):
        url = self.item.get('url', '').lower()
        if "youtube" in url or "youtu.be" in url:
            return ft.Icon(ft.Icons.SMART_DISPLAY, size=24, color=ft.Colors.RED_400)
        elif "t.me" in url or "telegram" in url:
            return ft.Icon(ft.Icons.TELEGRAM, size=24, color=ft.Colors.BLUE_400)
        elif "twitter" in url or "x.com" in url:
            return ft.Icon(ft.Icons.ALTERNATE_EMAIL, size=24, color=ft.Colors.WHITE)
        elif "instagram" in url:
            return ft.Icon(ft.Icons.CAMERA_ALT, size=24, color=ft.Colors.PINK_400)
        elif self.item.get("is_audio"):
            return ft.Icon(ft.Icons.AUDIO_FILE, size=24, color=Theme.TEXT_SECONDARY)
        elif self.item.get("is_playlist"):
            return ft.Icon(ft.Icons.PLAYLIST_PLAY, size=24, color=Theme.TEXT_SECONDARY)
        else:
            return ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=24, color=Theme.TEXT_SECONDARY)

    def build(self):
        # Modern Card Design with "Glassmorphism" feel
        bg_color = (
            Theme.BG_CARD
            if not self.is_selected
            else ft.Colors.with_opacity(0.1, Theme.PRIMARY)
        )
        border_color = Theme.BORDER if not self.is_selected else Theme.PRIMARY

        return ft.Container(
            content=ft.Row([
                # Icon Container
                ft.Container(
                    content=self.icon,
                    width=50, height=50,
                    bgcolor=Theme.BG_DARK,
                    border_radius=12,
                    alignment=ft.alignment.center,
                    border=ft.border.all(1, Theme.BG_DARK)
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
                self.actions_row
            ], spacing=12),
            padding=12,
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=16,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._on_hover
        )

    def _on_hover(self, e):
        # e.control.bgcolor = Theme.BG_CARD if e.data == "true" and not self.is_selected else (Theme.BG_CARD if not self.is_selected else ft.Colors.with_opacity(0.1, Theme.PRIMARY))
        # e.control.update()
        pass

    def _update_actions(self):
        status = self.item.get("status", "Queued")
        actions = []

        if status in ["Downloading", "Processing"]:
            actions.append(
                ft.IconButton(
                    ft.Icons.STOP_CIRCLE_OUTLINED,
                    on_click=lambda e: self.on_cancel(self.item),
                    icon_size=24,
                    tooltip="Cancel",
                    icon_color=ft.Colors.RED_300,
                )
            )
        elif status in ["Error", "Cancelled"] and self.on_retry:
            actions.append(
                ft.IconButton(
                    ft.Icons.REFRESH,
                    on_click=lambda e: self.on_retry(self.item),
                    icon_size=24,
                    tooltip="Retry",
                    icon_color=Theme.WARNING,
                )
            )

        if status == "Queued":
            actions.insert(
                0,
                ft.Column(
                    [
                        ft.IconButton(
                            ft.Icons.KEYBOARD_ARROW_UP,
                            on_click=lambda e: self.on_reorder(self.item, -1),
                            icon_size=18,
                            tooltip="Move Up",
                            style=ft.ButtonStyle(padding=0, shape=ft.CircleBorder()),
                            icon_color=Theme.TEXT_SECONDARY,
                        ),
                        ft.IconButton(
                            ft.Icons.KEYBOARD_ARROW_DOWN,
                            on_click=lambda e: self.on_reorder(self.item, 1),
                            icon_size=18,
                            tooltip="Move Down",
                            style=ft.ButtonStyle(padding=0, shape=ft.CircleBorder()),
                            icon_color=Theme.TEXT_SECONDARY,
                        ),
                    ],
                    spacing=0,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            )

        actions.append(
            ft.IconButton(
                ft.Icons.DELETE_OUTLINE,
                on_click=lambda e: self.on_remove(self.item),
                icon_size=24,
                tooltip="Remove",
                icon_color=ft.Colors.GREY_500,
            )
        )
        self.actions_row.controls = actions
        if self.actions_row.page:
            self.actions_row.update()

    def update_progress(self):
        self.status_text.value = self.item['status']

        # Dynamic color for progress
        if self.item["status"] == "Error" or self.item["status"] == "Cancelled":
             self.status_text.color = Theme.ERROR
             self.progress_bar.color = Theme.ERROR
        elif self.item["status"] == "Completed":
             self.status_text.color = Theme.SUCCESS
             self.progress_bar.color = Theme.SUCCESS
        elif self.item["status"] == "Downloading":
             self.status_text.color = Theme.PRIMARY
             self.progress_bar.color = Theme.PRIMARY
        else:
             self.status_text.color = Theme.TEXT_SECONDARY
             self.progress_bar.color = Theme.PRIMARY

        if 'speed' in self.item and self.item['status'] == 'Downloading':
             self.details_text.value = f"{self.item.get('size', '')}  •  {self.item.get('speed', '')}  •  ETA: {self.item.get('eta', '')}"
        else:
             self.details_text.value = ""

        self.status_text.update()
        self.details_text.update()
        self.progress_bar.update()
        self.title_text.value = self.item.get('title', self.item['url'])
        self.title_text.update()
        self._update_actions()
