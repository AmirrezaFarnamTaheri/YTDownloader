"""History View"""

import logging

import flet as ft

from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import open_folder
from views.base_view import BaseView
from views.components.history_item import HistoryItemControl


class HistoryView(BaseView):
    """View for displaying download history."""

    def __init__(self):
        super().__init__(LM.get("history"), ft.icons.HISTORY)

        self.history_list = ft.ListView(expand=True, spacing=10, padding=10)

        # Header actions
        self.clear_btn = ft.OutlinedButton(
            LM.get("clear_history"),
            icon=ft.icons.DELETE_SWEEP,
            on_click=self.clear_history,
            style=ft.ButtonStyle(
                color=Theme.Status.ERROR,
                side=ft.BorderSide(1, Theme.Status.ERROR),
            ),
        )

        self.add_control(
            ft.Row(
                [
                    ft.Container(expand=True),
                    self.clear_btn,
                ],
                alignment=ft.MainAxisAlignment.END,
            )
        )
        self.add_control(self.history_list)

    def load(self):
        """Loads history items from the database."""
        self.history_list.controls.clear()
        items = HistoryManager.get_history(limit=50)

        if not items:
            self.history_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.HISTORY, size=64, color=Theme.TEXT_MUTED),
                            ft.Text(
                                LM.get("no_history", "No history found"),
                                color=Theme.Text.SECONDARY,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
        else:
            for item in items:
                control = HistoryItemControl(
                    item,
                    on_open_folder=self.open_folder_safe,
                    on_copy_url=lambda u: self.page.set_clipboard(u),
                    on_delete=lambda x: None,  # Placeholder if we add single delete later
                )
                self.history_list.controls.append(control)

        self.update()

    def clear_history(self, e):
        """Clears the history with a confirmation dialog."""
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

        self.page.open(dlg)

    def open_folder_safe(self, path):
        """Safely opens the folder containing the downloaded file."""
        try:
            if path:
                open_folder(path, self.page)
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logging.error("Failed to open folder: %s", ex)
