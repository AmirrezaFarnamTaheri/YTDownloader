"""History View"""

import logging

import flet as ft

from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import open_folder
from views.base_view import BaseView
from views.components.history_item import HistoryItemControl

logger = logging.getLogger(__name__)


class HistoryView(BaseView):
    """View for displaying download history."""

    def __init__(self):
        super().__init__(LM.get("history"), ft.icons.HISTORY)

        self.history_list = ft.ListView(expand=True, spacing=10, padding=10)
        self.offset = 0
        self.limit = 50
        self.current_search = ""

        # Search Bar
        self.search_field = ft.TextField(
            expand=True,
            on_submit=self._on_search_submit,
            on_change=self._on_search_change,  # Live search
            **Theme.get_input_decoration(
                hint_text=LM.get("search_history", "Search history..."),
                prefix_icon=ft.icons.SEARCH,
            ),
        )

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

        # Load More Button
        self.load_more_btn = ft.ElevatedButton(
            LM.get("load_more", "Load More"),
            on_click=self._load_more,
            visible=False,
        )

        # Header Row
        header = ft.Row(
            [
                self.search_field,
                self.clear_btn,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.add_control(ft.Container(content=header, padding=10))
        self.add_control(self.history_list)
        self.add_control(
            ft.Container(content=self.load_more_btn, alignment=ft.alignment.center)
        )

    def load(self, reset=True):
        """Loads history items from the database."""
        if reset:
            self.offset = 0
            self.history_list.controls.clear()

        logger.debug(
            "Loading history items (offset=%d, query=%s)",
            self.offset,
            self.current_search,
        )

        if self.current_search:
            # Note: search_history expects page/limit logic differently or manually handled
            # But search_history returns dict with 'entries'.
            # We need to implement offset/limit in search_history if we want pagination there.
            # Assuming search_history returns all or limited list.
            # Ideally HistoryManager should support limit/offset for search too.
            # For now, we fallback to get_history if no query, or search_history.
            # HistoryManager.search_history returns ALL matches currently (no limit arg in signature in memory, but let's check).
            # If search_history doesn't support pagination, we might load all (careful).
            # Checking HistoryManager code... `limit` and `offset` arguments were added to `get_history`.
            # `search_history` has `LIMIT ? OFFSET ?` in SQL query?
            # Let's check `history_manager.py` content from previous reads.
            # `search_history` implemented `SELECT * FROM history ...` without limit/offset args in Python method signature.
            # We will use `get_history` with `search_query` arg which was added in previous refactor?
            # Wait, I read `history_manager.py` earlier. `get_history` has `search_query` arg.
            # `def get_history(self, limit: int = 50, offset: int = 0, search_query: str = "")`
            # Yes! So we can use that.
            items = HistoryManager.get_history(
                limit=self.limit, offset=self.offset, search_query=self.current_search
            )
        else:
            # Explicitly pass empty search query to match test expectation/API consistency
            items = HistoryManager.get_history(
                limit=self.limit, offset=self.offset, search_query=""
            )

        if not items and self.offset == 0:
            logger.info("History list is empty")
            self.history_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.HISTORY, size=64, color=Theme.TEXT_MUTED),
                            ft.Text(
                                LM.get("no_history"),
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
            self.load_more_btn.visible = False
        else:
            for item in items:
                control = HistoryItemControl(
                    item,
                    on_open_folder=self.open_folder_safe,
                    on_copy_url=self._copy_url_safe,
                    on_delete=self._delete_item,
                )
                self.history_list.controls.append(control)

            # Show load more if we got a full page
            self.load_more_btn.visible = len(items) == self.limit

        self.update()

    def _on_search_submit(self, e):
        self.current_search = self.search_field.value.strip()
        self.load(reset=True)

    def _on_search_change(self, e):
        # Optional: Debounce here if needed. For now, simple live search on enter or explicit.
        # But user might expect live search.
        # Let's stick to submit for performance or use a simple check.
        val = self.search_field.value.strip()
        if not val:
            self.current_search = ""
            self.load(reset=True)

    def _load_more(self, e):
        self.offset += self.limit
        self.load(reset=False)

    def clear_history(self, e):
        """Clears the history with a confirmation dialog."""
        # Create dialog instance first
        # pylint: disable=unused-argument
        dlg = ft.AlertDialog(modal=True)

        def close_dlg(e):
            self.page.close(dlg)

        def confirm_clear(e):
            try:
                logger.info("User confirmed history clear")
                HistoryManager.clear_history()
                self.load()
                if self.page:
                    self.page.open(
                        ft.SnackBar(content=ft.Text(LM.get("history_cleared")))
                    )
            except Exception as ex:  # pylint: disable=broad-exception-caught
                logger.error("Failed to clear history: %s", ex)
                if self.page:
                    self.page.open(
                        ft.SnackBar(content=ft.Text(LM.get("history_clear_failed")))
                    )
            finally:
                if self.page:
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
                logger.debug("Opening history folder: %s", path)
                open_folder(path, self.page)
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("Failed to open folder: %s", ex)
            if self.page:
                self.page.open(
                    ft.SnackBar(content=ft.Text(LM.get("open_folder_failed")))
                )

    def _copy_url_safe(self, url: str):
        """Safely copies URL to clipboard."""
        if url and self.page:
            try:
                self.page.set_clipboard(url)
                self.page.open(
                    ft.SnackBar(content=ft.Text(LM.get("url_copied", "URL copied")))
                )
            except Exception as ex:  # pylint: disable=broad-exception-caught
                logger.error("Failed to copy URL: %s", ex)

    def _delete_item(self, item: dict):
        """Deletes a single history item."""
        try:
            item_id = item.get("id")
            if item_id:
                HistoryManager.delete_entry(item_id)
                self.load()  # Reload the list
                if self.page:
                    self.page.open(
                        ft.SnackBar(
                            content=ft.Text(LM.get("item_deleted", "Item deleted"))
                        )
                    )
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("Failed to delete history item: %s", ex)
