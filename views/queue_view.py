"""
Queue View module.

Displays the list of active, queued, and completed downloads.
Refactored to use DownloadItemControl with bulk actions support.
"""

import logging
from collections.abc import Callable
from typing import Any

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
        on_cancel: Callable[[dict[str, Any]], None],
        on_remove: Callable[[dict[str, Any]], None],
        on_reorder: Callable[[int, int], None],
        on_play: Callable[[dict[str, Any]], None],
        on_open_folder: Callable[[dict[str, Any]], None],
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

        self.pause_all_btn = ft.OutlinedButton(
            LM.get("pause_all", "Pause All"),
            icon=ft.icons.PAUSE_CIRCLE_OUTLINE_ROUNDED,
            on_click=self._on_pause_all,
            style=ft.ButtonStyle(
                color=Theme.Status.WARNING,
                side=ft.BorderSide(1, Theme.Status.WARNING),
            ),
        )

        self.resume_all_btn = ft.OutlinedButton(
            LM.get("resume_all", "Resume All"),
            icon=ft.icons.PLAY_CIRCLE_OUTLINE_ROUNDED,
            on_click=self._on_resume_all,
            style=ft.ButtonStyle(
                color=Theme.Status.SUCCESS,
                side=ft.BorderSide(1, Theme.Status.SUCCESS),
            ),
        )

        self.clear_completed_btn = ft.OutlinedButton(
            LM.get("clear_completed", "Clear Completed"),
            icon=ft.icons.DELETE_SWEEP_ROUNDED,
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
                self.pause_all_btn,
                self.resume_all_btn,
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

        # Build the content layout - header above the list view
        self.selected_index = 0
        self.content_col.controls.append(self.header_row)
        self.content_col.controls.append(self.list_view)

    def _safe_update(self, control: ft.Control | None = None) -> None:
        """Update control only when mounted; skip detached-control update errors."""
        target: ft.Control = control or self
        try:
            target.update()
        except Exception as ex:  # pylint: disable=broad-exception-caught
            if "Control must be added to the page first" in str(ex):
                logger.debug(
                    "Skipping update for detached control: %s", target.__class__.__name__
                )
                return
            raise

    def rebuild(self):
        """Updates the list of items using diff logic to minimize redraws."""
        items = self.queue_manager.get_all()
        self._update_stats(items)

        # Handle Empty State
        if not items:
            if not self.list_view.controls or isinstance(
                self.list_view.controls[0], DownloadItemControl
            ):
                self.list_view.controls.clear()
                self.list_view.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.icons.QUEUE, size=64, color=Theme.TEXT_MUTED
                                ),
                                ft.Text(
                                    LM.get("no_items_found"),
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
                self.cancel_all_btn.disabled = True
                self.clear_completed_btn.disabled = True
                self.pause_all_btn.disabled = True
                self.resume_all_btn.disabled = True
                self._safe_update()
            return

        # If previous state was empty/placeholder, clear it first
        if self.list_view.controls and not isinstance(
            self.list_view.controls[0], DownloadItemControl
        ):
            self.list_view.controls.clear()

        # --- Diff Logic ---
        # Map existing controls by item ID
        existing_controls = {
            c.item.get("id"): c
            for c in self.list_view.controls
            if isinstance(c, DownloadItemControl)
        }

        # Reconstruct list in correct order
        new_controls_list = []
        for item in items:
            item_id = item.get("id")
            if item_id in existing_controls:
                # Reuse existing control and update state
                ctrl = existing_controls[item_id]
                ctrl.update_state(item)
                new_controls_list.append(ctrl)
            else:
                # Create new
                control = DownloadItemControl(
                    item,
                    on_cancel=self.on_cancel,
                    on_retry=self.on_retry,
                    on_remove=self.on_remove,
                    on_play=self.on_play,
                    on_open_folder=self.on_open_folder,
                )
                new_controls_list.append(control)

        # Bulk Actions State
        has_active = any(
            item.get("status") in ("Downloading", "Queued", "Processing", "Allocating")
            for item in items
        )
        has_queued = any(item.get("status") == "Queued" for item in items)
        has_paused = any(item.get("status") == "Paused" for item in items)
        has_completed = any(
            item.get("status") in ("Completed", "Error", "Cancelled") for item in items
        )
        self.cancel_all_btn.disabled = not has_active
        self.pause_all_btn.disabled = not has_queued
        self.resume_all_btn.disabled = not has_paused
        self.clear_completed_btn.disabled = not has_completed

        # Check for structure changes
        structure_changed = False
        if len(self.list_view.controls) != len(new_controls_list):
            structure_changed = True
        else:
            for i, c in enumerate(new_controls_list):
                if self.list_view.controls[i] is not c:
                    structure_changed = True
                    break

        if structure_changed:
            self.list_view.controls = new_controls_list
            self._safe_update()
        else:
            # Only update auxiliary controls
            self._safe_update(self.stats_text)
            self._safe_update(self.cancel_all_btn)
            self._safe_update(self.pause_all_btn)
            self._safe_update(self.resume_all_btn)
            self._safe_update(self.clear_completed_btn)

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
            parts.append(
                LM.get("stats_downloading", "{0} downloading").format(downloading)
            )
        if queued > 0:
            parts.append(LM.get("stats_queued", "{0} queued").format(queued))
        if completed > 0:
            parts.append(LM.get("stats_completed", "{0} completed").format(completed))
        if failed > 0:
            parts.append(LM.get("stats_failed", "{0} failed").format(failed))

        self.stats_text.value = (
            f"{total} {LM.get('items', 'items')} | " + ", ".join(parts)
            if parts
            else f"{total} {LM.get('items', 'items')}"
        )

    # pylint: disable=unused-argument
    def _on_cancel_all(self, e):
        """Cancel all active downloads."""
        logger.info("User requested cancel all downloads")
        try:
            self.queue_manager.cancel_all()
            self.rebuild()
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(
                            LM.get("all_downloads_cancelled", "All downloads cancelled")
                        )
                    )
                )
        except Exception as ex:
            logger.error("Failed to cancel all: %s", ex)

    # pylint: disable=unused-argument
    def _on_pause_all(self, e):
        """Pause all queued downloads."""
        try:
            paused = self.queue_manager.pause_all()
            self.rebuild()
            if self.page and paused > 0:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(
                            LM.get("paused_items", "Paused {0} items").format(paused)
                        )
                    )
                )
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("Failed to pause all: %s", ex)

    # pylint: disable=unused-argument
    def _on_resume_all(self, e):
        """Resume all paused downloads."""
        try:
            resumed = self.queue_manager.resume_all()
            self.rebuild()
            if self.page and resumed > 0:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(
                            LM.get("resumed_items", "Resumed {0} items").format(resumed)
                        )
                    )
                )
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("Failed to resume all: %s", ex)

    # pylint: disable=unused-argument
    def _on_clear_completed(self, e):
        """Remove all completed, errored, and cancelled items from queue."""
        logger.info("User requested clear completed downloads")
        try:
            removed_count = 0
            if hasattr(self.queue_manager, "clear_completed"):
                removed_count = int(self.queue_manager.clear_completed())
            else:
                items = self.queue_manager.get_all()
                for item in items:
                    if item.get("status") in ("Completed", "Error", "Cancelled"):
                        self.queue_manager.remove_item(item)
                        removed_count += 1
            self.rebuild()
            if self.page and removed_count > 0:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(
                            LM.get("cleared_items", "Cleared {0} items").format(
                                removed_count
                            )
                        )
                    )
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
