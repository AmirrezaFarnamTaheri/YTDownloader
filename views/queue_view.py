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
        """Highlight selected item."""
        if not self._item_controls:
            return

        items = self.queue_manager.get_all()
        if not items:
            return

        # Clamp index
        if index < 0: index = 0
        if index >= len(items): index = len(items) - 1

        self.selected_index = index

        # Update UI selection state
        # We need to iterate through controls and set is_selected
        # This is a bit inefficient for large lists but functional for now
        for i, item in enumerate(items):
            ctrl = item.get("control")
            if ctrl:
                is_sel = (i == self.selected_index)
                if ctrl.is_selected != is_sel:
                    ctrl.is_selected = is_sel
                    # Rebuild the view content for selection style
                    ctrl.view.bgcolor = (
                        ft.Colors.with_opacity(0.1, Theme.PRIMARY) if is_sel else Theme.BG_CARD
                    )
                    ctrl.view.update()

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
