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

        self.queue_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        self.clear_btn = ft.OutlinedButton(
            "Clear Finished",
            icon=ft.Icons.CLEAR_ALL,
            on_click=self.clear_finished,
            style=ft.ButtonStyle(color=Theme.TEXT_SECONDARY)
        )

        self.content_col.controls.insert(1, ft.Row([ft.Container(expand=True), self.clear_btn]))
        self.add_control(self.queue_list)

    def rebuild(self):
        self.queue_list.controls.clear()
        items = self.queue_manager.get_all()
        for i, item in enumerate(items):
            # We need to persist the control if it exists to keep progress state visible smoothly?
            # Or better: create new control but init with current state.
            # The DownloadItemControl in components.py handles UI.
            # If we recreate it, the progress bar jumps to 0 then back to value on next update.
            # To avoid this, we should reuse the control stored in item['control'] if valid.

            if 'control' in item and isinstance(item['control'], DownloadItemControl):
                # Just re-append the existing view
                # But wait, Flet controls cannot be in two places.
                # If we clear(), they are detached. We can re-add them.
                # However, if the order changed, we need to re-add in correct order.
                pass
            else:
                control = DownloadItemControl(item, self.on_cancel, self.on_remove, self.on_reorder)
                item['control'] = control

            self.queue_list.controls.append(item['control'].view)
        self.update()

    def clear_finished(self, e):
        to_remove = [item for item in self.queue_manager.get_all() if item['status'] in ('Completed', 'Cancelled', 'Error')]
        for item in to_remove:
            self.on_remove(item)
        self.rebuild()
