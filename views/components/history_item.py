"""
History Item Control.

Represents a single completed download in the History list.
Features file info and file actions.
"""

import logging
from collections.abc import Callable
from typing import Any

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme

logger = logging.getLogger(__name__)


class HistoryItemControl(ft.Container):
    """
    A card-like control representing a history item.
    """

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def __init__(
        self,
        item: dict[str, Any],
        on_open_folder: Callable,
        on_copy_url: Callable,
        on_delete: Callable,  # Added delete capability for individual items if needed
    ):
        super().__init__()
        self.item = item
        self.on_open_folder = on_open_folder
        self.on_copy_url = on_copy_url
        self.on_delete = on_delete

        # Apply standardized card decoration
        card_style = Theme.get_card_decoration()
        for key, value in card_style.items():
            setattr(self, key, value)

        self.padding = 15

        # UI Components
        title = item.get("title", item.get("url", LM.get("unknown_title")))
        self.title_text = ft.Text(
            title,
            weight=ft.FontWeight.BOLD,
            size=16,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=Theme.Text.PRIMARY,
        )

        timestamp = item.get("timestamp", LM.get("unknown_date"))
        filesize = item.get("file_size", LM.get("not_available"))
        self.meta_text = ft.Text(
            f"{timestamp} | {filesize}",
            size=12,
            color=Theme.Text.SECONDARY,
        )

        # Icon
        self.icon = ft.Icon(ft.icons.CHECK_CIRCLE, color=Theme.Status.SUCCESS, size=28)

        # Actions
        self.action_row = ft.Row(
            controls=[
                ft.IconButton(
                    ft.icons.FOLDER_OPEN,
                    tooltip=LM.get("open_folder"),
                    icon_color=Theme.Primary.MAIN,
                    on_click=lambda _: self.on_open_folder(
                        self.item.get("output_path")
                    ),
                ),
                ft.IconButton(
                    ft.icons.CONTENT_COPY,
                    tooltip=LM.get("copy_url"),
                    icon_color=Theme.Text.SECONDARY,
                    on_click=lambda _: self.on_copy_url(self.item.get("url")),
                ),
            ],
            spacing=0,
        )

        # Layout
        self.content = ft.Row(
            [
                self.icon,
                ft.Container(width=10),
                ft.Column(
                    [self.title_text, self.meta_text],
                    spacing=2,
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                self.action_row,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
