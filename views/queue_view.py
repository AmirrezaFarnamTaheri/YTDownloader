"""
Queue View module.

Displays the list of active, queued, and completed downloads.
Refactored to use DownloadItemControl with bulk actions support.
"""

import logging
from typing import Any, Callable, Dict

import flet as ft

from localization_manager import LocalizationManager as LM
from queue_manager import QueueManager
from theme import Theme
from views.base_view import BaseView
from views.components.download_item import DownloadItemControl

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class QueueView(BaseView):
    """
    View for managing the download queue.

    Features:
    - Display all queued, active, and completed downloads
    - Bulk actions (cancel all, clear completed)
    - Keyboard navigation support
    - Item-level actions (cancel, retry, remove, play, open folder)
    """

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        queue_manager: QueueManager,
        on_cancel: Callable[[Dict[str, Any]], None],
        on_remove: Callable[[Dict[str, Any]], None],
        on_reorder: Callable[[int, int], None],
        on_play: Callable[[Dict[str, Any]], None],
        on_open_folder: Callable[[Dict[str, Any]], None],
    ):
        super().__init__(LM.get("queue"), ft.icons.QUEUE_MUSIC)
        self.queue_manager = queue_manager
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.on_play = on_play
        self.on_open_folder = on_open_folder
        # Use queue manager's retry method
        self.on_retry = lambda item: self.queue_manager.retry_item(item.get("id"))

        # Queue statistics text
        self.stats_text = ft.Text(
            "",
            size=12,
            color=Theme.Text.SECONDARY,
        )

        # Bulk action buttons
        self.cancel_all_btn = ft.OutlinedButton(
            LM.get("cancel_all", "Cancel All"),
            icon=ft.icons.CANCEL,
            on_click=self._on_cancel_all,
            style=ft.ButtonStyle(
                color=Theme.Status.ERROR,
                side=ft.BorderSide(1, Theme.Status.ERROR),
            ),
        )

        self.clear_completed_btn = ft.OutlinedButton(
            LM.get("clear_completed", "Clear Completed"),
            icon=ft.icons.DELETE_SWEEP,
            on_click=self._on_clear_completed,
            style=ft.ButtonStyle(
                color=Theme.Text.SECONDARY,
                side=ft.BorderSide(1, Theme.Text.SECONDARY),
            ),
        )

        # Header with actions
        self.header_row = ft.Row(
            [
                self.stats_text,
                ft.Container(expand=True),
                self.clear_completed_btn,
                self.cancel_all_btn,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.list_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=False,
        )

        # Add header and list to content
        self.add_control(self.header_row)
        self.controls = [self.list_view]
        self.selected_index = 0

    def rebuild(self):
        """Rebuilds the list of items and updates statistics."""
        items = self.queue_manager.get_all()
        self.list_view.controls.clear()

        # Update statistics
        self._update_stats(items)

        if not items:
            self.list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.QUEUE, size=64, color=Theme.TEXT_MUTED),
                            ft.Text(
                                LM.get("no_items_found"), color=Theme.Text.SECONDARY
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
            # Disable bulk actions when queue is empty
            self.cancel_all_btn.disabled = True
            self.clear_completed_btn.disabled = True
        else:
            for item in items:
                control = DownloadItemControl(
                    item,
                    on_cancel=self.on_cancel,
                    on_retry=self.on_retry,
                    on_remove=self.on_remove,
                    on_play=self.on_play,
                    on_open_folder=self.on_open_folder,
                )
                self.list_view.controls.append(control)

            # Enable/disable bulk actions based on queue state
            has_active = any(
                item.get("status") in ("Downloading", "Queued", "Processing", "Allocating")
                for item in items
            )
            has_completed = any(
                item.get("status") in ("Completed", "Error", "Cancelled")
                for item in items
            )
            self.cancel_all_btn.disabled = not has_active
            self.clear_completed_btn.disabled = not has_completed

        self.update()

    def _update_stats(self, items):
        """Update queue statistics display."""
        if not items:
            self.stats_text.value = LM.get("queue_empty", "Queue is empty")
            return

        total = len(items)
        downloading = sum(1 for i in items if i.get("status") == "Downloading")
        queued = sum(1 for i in items if i.get("status") == "Queued")
        completed = sum(1 for i in items if i.get("status") == "Completed")
        failed = sum(1 for i in items if i.get("status") in ("Error", "Cancelled"))

        parts = []
        if downloading > 0:
            parts.append(LM.get("stats_downloading", "{0} downloading").format(downloading))
        if queued > 0:
            parts.append(LM.get("stats_queued", "{0} queued").format(queued))
        if completed > 0:
            parts.append(LM.get("stats_completed", "{0} completed").format(completed))
        if failed > 0:
            parts.append(LM.get("stats_failed", "{0} failed").format(failed))

        self.stats_text.value = f"{total} {LM.get('items', 'items')} | " + ", ".join(parts) if parts else f"{total} {LM.get('items', 'items')}"

    def _on_cancel_all(self, e):
        """Cancel all active downloads."""
        logger.info("User requested cancel all downloads")
        try:
            self.queue_manager.cancel_all()
            self.rebuild()
            if self.page:
                self.page.open(
                    ft.SnackBar(content=ft.Text(LM.get("all_downloads_cancelled", "All downloads cancelled")))
                )
        except Exception as ex:
            logger.error("Failed to cancel all: %s", ex)

    def _on_clear_completed(self, e):
        """Remove all completed, errored, and cancelled items from queue."""
        logger.info("User requested clear completed downloads")
        try:
            items = self.queue_manager.get_all()
            removed_count = 0
            for item in items:
                if item.get("status") in ("Completed", "Error", "Cancelled"):
                    self.queue_manager.remove_item(item.get("id"))
                    removed_count += 1
            self.rebuild()
            if self.page and removed_count > 0:
                self.page.open(
                    ft.SnackBar(content=ft.Text(LM.get("cleared_items", "Cleared {0} items").format(removed_count)))
                )
        except Exception as ex:
            logger.error("Failed to clear completed: %s", ex)

    def select_item(self, index: int):
        """Highlight item at index (Keyboard nav)."""
        count = len(self.list_view.controls)
        if count == 0:
            return

        # Clamp
        index = max(0, min(index, count - 1))
        self.selected_index = index

        # Reset all borders/shadows
        for ctrl in self.list_view.controls:
            if isinstance(ctrl, DownloadItemControl):
                ctrl.border = None
                # Restore default shadow
                ctrl.shadow = ft.BoxShadow(
                    blur_radius=10,
                    color=ft.colors.with_opacity(0.1, ft.colors.BLACK),
                )
                ctrl.update()

        # Highlight selected
        selected = self.list_view.controls[index]
        if isinstance(selected, DownloadItemControl):
            selected.border = ft.border.all(2, Theme.Primary.MAIN)
            selected.shadow = ft.BoxShadow(
                blur_radius=15,
                color=ft.colors.with_opacity(0.4, Theme.Primary.MAIN),
            )
            selected.update()
            # Scroll to (Simple approximation)
            self.list_view.scroll_to(offset=index * 100, duration=300)

    def get_selected_item(self):
        """Return the currently selected item data."""
        if 0 <= self.selected_index < len(self.list_view.controls):
            ctrl = self.list_view.controls[self.selected_index]
            if isinstance(ctrl, DownloadItemControl):
                return ctrl.item
        return None
