import logging

import flet as ft

from theme import Theme
from views.components.download_item import DownloadItemControl

from .base_view import BaseView

logger = logging.getLogger(__name__)


class QueueView(BaseView):
    def __init__(self, queue_manager, on_cancel, on_remove, on_reorder):
        logger.debug("Initializing QueueView")
        super().__init__("Queue", ft.Icons.QUEUE_MUSIC)
        self.queue_manager = queue_manager
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.on_retry = None  # Will be set by main.py

        self.queue_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        self.clear_btn = ft.OutlinedButton(
            "Clear Finished",
            icon=ft.Icons.CLEAR_ALL,
            on_click=self.clear_finished,
            style=ft.ButtonStyle(color=Theme.TEXT_SECONDARY),
        )

        self.content_col.controls.insert(
            1, ft.Row([ft.Container(expand=True), self.clear_btn])
        )
        self.add_control(self.queue_list)
        self._item_controls = {}  # Cache controls by item id
        self.selected_index = -1

    def select_item(self, index: int):
        """Highlight selected item safely and efficiently."""
        items = self.queue_manager.get_all()
        if not items:
            self.selected_index = -1
            return

        # Clamp index to current list
        index = max(0, min(index, len(items) - 1))

        # Track old/new indices
        old_index = self.selected_index
        new_index = index
        self.selected_index = new_index

        # Helper to (re)style a single item if control exists
        def _apply_selection(i: int, selected: bool):
            try:
                item = items[i]
            except IndexError:
                return  # Queue changed between reads
            ctrl = item.get("control")
            if not ctrl:
                return
            if getattr(ctrl, "is_selected", None) == selected:
                return
            ctrl.is_selected = selected
            # Update container background only
            if hasattr(ctrl, "view"):
                ctrl.view.bgcolor = (
                    ft.Colors.with_opacity(0.1, Theme.PRIMARY) if selected else Theme.BG_CARD
                )
                ctrl.view.update()

        # Update only changed rows
        if old_index != -1 and old_index != new_index and old_index < len(items):
            _apply_selection(old_index, False)
        _apply_selection(new_index, True)

    def get_selected_item(self):
        items = self.queue_manager.get_all()
        if 0 <= self.selected_index < len(items):
            return items[self.selected_index]
        return None

    def rebuild(self):
        # logger.debug("Rebuilding QueueView...")
        self.queue_list.controls.clear()
        items = self.queue_manager.get_all()

        # Track which items are still in queue
        current_items = {id(item): item for item in items}

        # Remove controls for items no longer in queue
        to_remove = []
        for item_id, control in self._item_controls.items():
            if item_id not in current_items:
                to_remove.append(item_id)
                if hasattr(control, "cleanup"):
                    control.cleanup()

        for item_id in to_remove:
            del self._item_controls[item_id]

        for i, item in enumerate(items):
            item_id = id(item)

            # Reuse existing control if possible
            if item_id in self._item_controls:
                control = self._item_controls[item_id]
                # Just update progress if status changed
                if item["status"] != control.item.get("_last_status"):
                    control.update_progress()
                    item["_last_status"] = item["status"]
            else:
                # Create new control
                control = DownloadItemControl(
                    item,
                    self.on_cancel,
                    self.on_remove,
                    self.on_reorder,
                    on_retry=self.on_retry,
                )
                self._item_controls[item_id] = control
                item["_last_status"] = item["status"]

            item["control"] = control
            self.queue_list.controls.append(control.view)

        self.update()

    def clear_finished(self, e):
        logger.info("User requested clear of finished items")
        to_remove = [
            item
            for item in self.queue_manager.get_all()
            if item["status"] in ("Completed", "Cancelled", "Error")
        ]
        logger.info(f"Clearing {len(to_remove)} finished items")
        for item in to_remove:
            self.on_remove(item)
        self.rebuild()
