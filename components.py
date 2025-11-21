import flet as ft
from typing import Dict, Any, Optional
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
            bgcolor=ft.Colors.with_opacity(0.2, Theme.PRIMARY),
        )

        self.status_text = ft.Text(
            item["status"],
            size=12,
            color=Theme.TEXT_SECONDARY,
            weight=ft.FontWeight.W_500,
        )
        self.details_text = ft.Text("Waiting...", size=12, color=Theme.TEXT_MUTED)
        self.title_text = ft.Text(
            self.item.get("title", self.item["url"]),
            weight=ft.FontWeight.BOLD,
            size=15,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=Theme.TEXT_PRIMARY,
            max_lines=1,
        )

        # Action container will be updated dynamically
        self.actions_row = ft.Row(spacing=5, alignment=ft.MainAxisAlignment.END)
        self._update_actions()

        self.view = self.build()

    def build(self):
        bg_color = (
            Theme.BG_CARD
            if not self.is_selected
            else ft.Colors.with_opacity(0.1, Theme.PRIMARY)
        )

        # Platform specific icon
        url = self.item.get("url", "").lower()
        icon_data = ft.Icons.INSERT_DRIVE_FILE
        icon_color = Theme.TEXT_SECONDARY

        if "youtube" in url or "youtu.be" in url:
            icon_data = ft.Icons.ONDEMAND_VIDEO
            icon_color = ft.Colors.RED_400
        elif "t.me" in url or "telegram" in url:
            icon_data = ft.Icons.TELEGRAM
            icon_color = ft.Colors.BLUE_400
        elif "twitter" in url or "x.com" in url:
            icon_data = ft.Icons.ALTERNATE_EMAIL
            icon_color = ft.Colors.WHITE
        elif "instagram" in url:
            icon_data = ft.Icons.CAMERA_ALT
            icon_color = ft.Colors.PINK_400

        if self.item.get("is_audio"):
            icon_data = ft.Icons.AUDIO_FILE
        elif self.item.get("is_playlist"):
            icon_data = ft.Icons.PLAYLIST_PLAY

        return ft.Container(
            content=ft.Row(
                [
                    # Icon Container
                    ft.Container(
                        content=ft.Icon(icon_data, size=28, color=icon_color),
                        width=56,
                        height=56,
                        bgcolor=(
                            ft.Colors.with_opacity(0.1, icon_color)
                            if icon_color != Theme.TEXT_SECONDARY
                            else Theme.BG_DARK
                        ),
                        border_radius=12,
                        alignment=ft.alignment.center,
                    ),
                    # Info Column
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    self.title_text,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            self.progress_bar,
                            ft.Row(
                                [self.status_text, self.details_text],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        spacing=6,
                        expand=True,
                    ),
                    # Actions
                    self.actions_row,
                ],
                spacing=15,
            ),
            padding=15,
            bgcolor=bg_color,
            border_radius=16,
            shadow=(
                ft.BoxShadow(
                    blur_radius=10,
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                    offset=ft.Offset(0, 4),
                )
                if not self.is_selected
                else None
            ),
            border=(
                ft.border.all(1, Theme.BORDER)
                if not self.is_selected
                else ft.border.all(1, Theme.PRIMARY)
            ),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            margin=ft.margin.only(bottom=5),
        )

    def _update_actions(self):
        status = self.item.get("status", "Queued")
        actions = []

        if status in ["Downloading", "Processing", "Allocating"]:
            actions.append(
                ft.IconButton(
                    ft.Icons.CLOSE,
                    on_click=lambda e: self.on_cancel(self.item),
                    icon_size=20,
                    tooltip="Cancel",
                    icon_color=Theme.ERROR,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.with_opacity(0.1, Theme.ERROR),
                        shape=ft.CircleBorder(),
                    ),
                )
            )
        elif status in ["Error", "Cancelled"] and self.on_retry:
            actions.append(
                ft.IconButton(
                    ft.Icons.REFRESH,
                    on_click=lambda e: self.on_retry(self.item),
                    icon_size=20,
                    tooltip="Retry",
                    icon_color=Theme.WARNING,
                )
            )

        if status == "Queued" or status.startswith("Scheduled"):
            actions.append(
                ft.Column(
                    [
                        ft.IconButton(
                            ft.Icons.KEYBOARD_ARROW_UP,
                            on_click=lambda e: self.on_reorder(self.item, -1),
                            icon_size=18,
                            tooltip="Move Up",
                            style=ft.ButtonStyle(padding=0),
                            icon_color=Theme.TEXT_SECONDARY,
                        ),
                        ft.IconButton(
                            ft.Icons.KEYBOARD_ARROW_DOWN,
                            on_click=lambda e: self.on_reorder(self.item, 1),
                            icon_size=18,
                            tooltip="Move Down",
                            style=ft.ButtonStyle(padding=0),
                            icon_color=Theme.TEXT_SECONDARY,
                        ),
                    ],
                    spacing=0,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )

        if status not in ["Downloading", "Processing", "Allocating"]:
            actions.append(
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE,
                    on_click=lambda e: self.on_remove(self.item),
                    icon_size=20,
                    tooltip="Remove",
                    icon_color=Theme.TEXT_SECONDARY,
                )
            )

        self.actions_row.controls = actions
        if self.actions_row.page:
            self.actions_row.update()

    def update_progress(self):
        self.status_text.value = self.item["status"]

        # Dynamic color for progress
        if self.item["status"] == "Error" or self.item["status"] == "Cancelled":
            self.progress_bar.color = Theme.ERROR
            self.status_text.color = Theme.ERROR
        elif self.item["status"] == "Completed":
            self.progress_bar.color = Theme.SUCCESS
            self.status_text.color = Theme.SUCCESS
        else:
            self.progress_bar.color = Theme.PRIMARY
            self.status_text.color = Theme.TEXT_SECONDARY

        if "speed" in self.item and self.item["status"] in [
            "Downloading",
            "Processing",
        ]:
            self.details_text.value = f"{self.item.get('size', '')} • {self.item.get('speed', '')} • ETA: {self.item.get('eta', '')}"
        else:
            self.details_text.value = ""

        self.status_text.update()
        self.details_text.update()
        self.progress_bar.update()
        self.title_text.value = self.item.get("title", self.item["url"])
        self.title_text.update()

        self._update_actions()
