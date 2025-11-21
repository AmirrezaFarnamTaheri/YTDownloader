import flet as ft
from theme import Theme
from .base_view import BaseView
from components import DownloadItemControl


class QueueView(BaseView):
    def __init__(self, queue_manager, on_cancel, on_remove, on_reorder):
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

    def rebuild(self):
        self.queue_list.controls.clear()
        items = self.queue_manager.get_all()
        for i, item in enumerate(items):
            # We recreate controls to ensure state updates (like adding Retry button) are reflected
            # if status changed. Since we don't have partial UI updates in DownloadItemControl yet.
            # Actually, we should try to reuse if possible, but for now, let's recreate to support the new "Retry" button logic in constructor.

            # To support reuse, we'd need to update the control with new callbacks if they changed,
            # or the control needs to know about on_retry.

            # Let's create a new control for now to be safe with the new Retry feature.
            # Or check if it exists and update it.

            control = DownloadItemControl(
                item,
                self.on_cancel,
                self.on_remove,
                self.on_reorder,
                on_retry=self.on_retry,
            )
            item["control"] = control
            self.queue_list.controls.append(control.view)

            # Restore progress if downloading
            if item["status"] == "Downloading":
                control.update_progress()

        self.update()

    def clear_finished(self, e):
        to_remove = [
            item
            for item in self.queue_manager.get_all()
            if item["status"] in ("Completed", "Cancelled", "Error")
        ]
        for item in to_remove:
            self.on_remove(item)
        self.rebuild()
