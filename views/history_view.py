"""History View"""
import logging

import flet as ft

from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import open_folder

from .base_view import BaseView

# pylint: disable=missing-class-docstring

class HistoryView(BaseView):
    def __init__(self):
        super().__init__(LM.get("history"), ft.icons.HISTORY)

        self.history_list = ft.ListView(expand=True, spacing=10)
        self.add_control(
            ft.Row(
                [
                    ft.Container(expand=True),
                    ft.OutlinedButton(
                        LM.get("clear_history"),
                        icon=ft.icons.DELETE_SWEEP,
                        on_click=self.clear_history,
                    ),
                ]
            )
        )
# pylint: disable=missing-function-docstring
        self.add_control(self.history_list)

# pylint: disable=missing-function-docstring
    def load(self):
        self.history_list.controls.clear()
        items = HistoryManager.get_history(limit=50)
        for item in items:
            self.history_list.controls.append(self._create_item(item))
        self.update()

    def _create_item(self, item):
        return ft.Container(
            padding=15,
            bgcolor=Theme.BG_CARD,
            border_radius=8,
            content=ft.Row(
                [
                    ft.Icon(ft.icons.CHECK_CIRCLE, color=Theme.SUCCESS),
                    ft.Column(
                        [
                            ft.Text(
                                item.get("title", item["url"]),
                                weight=ft.FontWeight.BOLD,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                width=400,
                                color=Theme.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                f"{item.get('timestamp')} | {item.get('file_size', 'N/A')}",
                                size=12,
                                color=Theme.TEXT_SECONDARY,
                            ),
                        ]
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.icons.FOLDER_OPEN,
                        tooltip=LM.get("open_folder"),
                        icon_color=Theme.PRIMARY,
                        on_click=lambda e, p=item.get(
                            "output_path"
                        ): self.open_folder_safe(p),
                    ),
                    ft.IconButton(
                        ft.icons.COPY,
                        tooltip=LM.get("copy_url"),
                        icon_color=Theme.TEXT_SECONDARY,
                        on_click=lambda e, u=item["url"]: self.page.set_clipboard(u),
                    ),
                ]
# pylint: disable=missing-function-docstring
            ),
        )

# pylint: disable=missing-function-docstring
# pylint: disable=unused-argument
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-function-docstring
    def clear_history(self, e):
        # Create dialog instance first
# pylint: disable=unused-argument
        dlg = ft.AlertDialog(modal=True)

        def close_dlg(e):
            self.page.close(dlg)

        def confirm_clear(e):
            HistoryManager.clear_history()
            self.load()
            self.page.close(dlg)

        # Configure dialog
        dlg.title = ft.Text(LM.get("confirm_clear_history"))
        dlg.actions = [
            ft.TextButton(LM.get("yes"), on_click=confirm_clear),
            ft.TextButton(LM.get("no"), on_click=close_dlg),
        ]
        dlg.actions_alignment = ft.MainAxisAlignment.END

# pylint: disable=missing-function-docstring
        self.page.open(dlg)

# pylint: disable=broad-exception-caught
# pylint: disable=logging-fstring-interpolation
    def open_folder_safe(self, path):
        try:
            open_folder(path)
        except Exception as ex:
            logging.error(f"Failed to open folder: {ex}")
