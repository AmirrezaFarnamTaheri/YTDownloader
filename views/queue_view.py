"""
Queue View module.

Displays the list of active, queued, and completed downloads.
Refactored to use DownloadItemControl.
"""

from typing import Callable, List, Optional

import flet as ft

from localization_manager import LocalizationManager as LM
from queue_manager import QueueManager
from theme import Theme
from views.base_view import BaseView
from views.components.download_item import DownloadItemControl


class QueueView(BaseView):
    """
    View for managing the download queue.
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        on_cancel: Callable,
        on_remove: Callable,
        on_reorder: Callable,
        on_play: Callable,        # New
        on_open_folder: Callable, # New
    ):
        super().__init__(LM.get("queue"), ft.Icons.QUEUE_MUSIC)
        self.queue_manager = queue_manager
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.on_play = on_play
        self.on_open_folder = on_open_folder
        self.on_retry: Optional[Callable] = None  # Set externally

        self.list_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=False,
        )

        self.controls = [self.list_view]
        self.selected_index = 0

    def rebuild(self):
        """Rebuilds the list of items."""
        items = self.queue_manager.get_all()
        self.list_view.controls.clear()

        if not items:
            self.list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.QUEUE, size=64, color=Theme.TEXT_MUTED),
                            ft.Text(LM.get("no_items_found"), color=Theme.Text.SECONDARY),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                    height=300 # Approximate center
                )
            )
        else:
            for i, item in enumerate(items):
                control = DownloadItemControl(
                    item,
                    on_cancel=self.on_cancel,
                    on_retry=self.on_retry or (lambda x: None),
                    on_remove=self.on_remove,
                    on_play=self.on_play,
                    on_open_folder=self.on_open_folder,
                )
                self.list_view.controls.append(control)

        self.update()

    def select_item(self, index: int):
        """Highlight item at index (Keyboard nav)."""
        count = len(self.list_view.controls)
        if count == 0:
            return

        # Clamp
        index = max(0, min(index, count - 1))
        self.selected_index = index

        # Reset all borders
        for ctrl in self.list_view.controls:
            if isinstance(ctrl, DownloadItemControl):
                ctrl.border = None
                ctrl.update()

        # Highlight selected
        selected = self.list_view.controls[index]
        if isinstance(selected, DownloadItemControl):
            selected.border = ft.border.all(2, Theme.Primary.MAIN)
            selected.update()
            # Scroll to (Simple approximation)
            self.list_view.scroll_to(offset=index * 80, duration=300)

    def get_selected_item(self):
        """Return the currently selected item data."""
        if 0 <= self.selected_index < len(self.list_view.controls):
            ctrl = self.list_view.controls[self.selected_index]
            if isinstance(ctrl, DownloadItemControl):
                return ctrl.item
        return None
