"""
AppController module.
Handles application logic, callbacks, and bridging between UI and backend.
Refactored to delegate responsibilities.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, cast

import flet as ft

from app_state import state
from batch_importer import BatchImporter
from clipboard_monitor import start_clipboard_monitor
from download_scheduler import DownloadScheduler
from localization_manager import LocalizationManager as LM

# Helpers
from rate_limiter import RateLimiter
from tasks import fetch_info_task, process_queue
from ui_manager import UIManager
from ui_utils import (
    get_default_download_path,
    is_safe_path,
    normalize_download_target,
    open_folder,
    play_file,
    run_on_ui_thread,
    validate_download_target,
    validate_url,
)

logger = logging.getLogger(__name__)


class AppController:
    """
    Controller for the main application.
    Manages interactions between the UI (View) and the Backend (Model/Logic).
    Refactored to delegate responsibilities.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, page: ft.Page, ui_manager: UIManager):
        self.page = page
        self.ui = ui_manager
        self.active_threads: list[threading.Thread] = []
        self._clipboard_monitor_started = False

        # Delegates
        # Rate limiter for "add to queue" actions: 4 actions/sec, burst up to 10.
        # Generous enough not to frustrate batch/paste workflows but still
        # protects against accidental double-clicks and runaway automation.
        self.rate_limiter = RateLimiter(rate=4.0, capacity=10.0)
        self.batch_importer = BatchImporter(state.queue_manager, state.config)
        self.scheduler = DownloadScheduler()

        # Initialize Pickers
        # The picker is shared between batch import, history export and history
        # import, so the pending action decides how a result is handled.
        self._picker_action = "batch_import"
        self.file_picker = ft.FilePicker()
        self.time_picker = ft.TimePicker(
            confirm_text=LM.get("schedule_download"),
            error_invalid_text=LM.get("time_invalid"),
            help_text=LM.get("schedule_help_text"),
        )
        self.page.overlay.append(self.file_picker)
        self.page.overlay.append(self.time_picker)

        # Wire up pickers
        self.file_picker.on_result = self.on_file_picker_result
        self.time_picker.on_change = self.on_time_picked

    def start_background_loop(self):
        """Starts the background processing loop."""
        bg_thread = threading.Thread(
            target=self._background_loop, daemon=True, name="BackgroundLoop"
        )
        self.active_threads.append(bg_thread)
        bg_thread.start()

    def start_clipboard_monitor(self):
        """Starts the clipboard monitor."""
        if self.ui.download_view:
            started = start_clipboard_monitor(self.page, self.ui.download_view)
            if started:
                self._clipboard_monitor_started = True

    def cleanup(self):
        """Clean up resources on shutdown."""
        logger.info("Controller cleaning up...")
        state.cleanup()
        for thread in self.active_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        logger.info("Cleanup complete")

    def _background_loop(self):
        """
        Background loop for queue processing.
        Waits for signals from QueueManager and periodically refreshes the UI
        so progress bars and status badges track download progress smoothly.
        """
        logger.info("Background loop started.")
        ui_refresh_interval = 0.5  # seconds between queue-view repaints
        last_ui_refresh = 0.0

        while not state.shutdown_flag.is_set():
            try:
                # Wait briefly for work; timeout controls UI-refresh cadence.
                state.queue_manager.wait_for_items(timeout=ui_refresh_interval)

                if state.shutdown_flag.is_set():
                    break

                # Check scheduled items
                if state.queue_manager.update_scheduled_items(datetime.now()) > 0:
                    run_on_ui_thread(self.page, self.ui.update_queue_view)
                    last_ui_refresh = time.time()

                # Submit newly-ready items
                process_queue(self.page)

                # Periodically refresh queue-view so progress bars stay live
                now = time.time()
                if state.queue_manager.any_downloading() or (
                    now - last_ui_refresh >= ui_refresh_interval
                ):
                    run_on_ui_thread(self.page, self.ui.update_queue_view)
                    last_ui_refresh = now

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error in background_loop: %s", e, exc_info=True)
                time.sleep(1)
        logger.info("Background loop stopped.")

    # --- Callbacks ---

    def on_fetch_info(self, url: str):
        """Callback to fetch video information."""
        logger.info("User requested video info fetch for: %s", url)
        if not url:
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("url_required"))))
            return

        target = normalize_download_target(url)
        if not target:
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("error_invalid_url"))))
            return

        # Defence in depth: direct URLs must pass the SSRF-aware validator
        # before they ever reach the network layer. Search pseudo-URLs
        # (ytsearchN:query) are validated by normalize_download_target.
        if target == url and not validate_url(target):
            logger.warning("Rejected unsafe fetch target: %s", url)
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("error_invalid_url"))))
            return

        if self.ui.download_view:
            if hasattr(self.ui.download_view, "set_fetch_disabled"):
                self.ui.download_view.set_fetch_disabled(True)
            fetch_btn = getattr(self.ui.download_view, "fetch_btn", None)
            if fetch_btn is not None:
                fetch_btn.disabled = True
        self.page.update()

        logger.debug("Starting fetch_info_task thread...")
        threading.Thread(
            target=fetch_info_task,
            args=(target, self.ui.download_view, self.page),
            daemon=True,
        ).start()

    def on_add_to_queue(self, data: dict[str, Any]):
        """Callback to add an item to the download queue."""
        raw_url = data.get("url", "")
        logger.info("User requested add to queue: %s", raw_url)
        if not validate_download_target(raw_url):
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("error_invalid_url"))))
            return

        normalized_url = normalize_download_target(raw_url)
        if not normalized_url:
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("error_invalid_url"))))
            return

        # Rate limiting
        if not self.rate_limiter.check():
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("rate_limited"))))
            return

        # Scheduling
        status, sched_dt = self.scheduler.prepare_schedule(state.scheduled_time)
        if sched_dt:
            self.page.open(
                ft.SnackBar(
                    content=ft.Text(
                        LM.get(
                            "download_scheduled",
                            sched_dt.strftime("%Y-%m-%d %H:%M"),
                        )
                    )
                )
            )

        data = dict(data)
        data["url"] = normalized_url

        title = normalized_url
        video_info = state.get_video_info(normalized_url) or state.get_video_info(
            raw_url
        )
        if video_info:
            title = video_info.get("title", normalized_url)
        elif (
            state.video_info
            and self.ui.download_view
            and raw_url == self.ui.download_view.input_card.url_input.value
        ):
            title = state.video_info.get("title", normalized_url)

        download_path = get_default_download_path(state.config.get("download_path"))
        proxy = state.config.get("proxy") or None
        rate_limit = state.config.get("rate_limit") or None

        item = {
            "url": data["url"],
            "title": title,
            "status": status,
            "scheduled_time": sched_dt,
            "video_format": data.get("video_format"),
            "audio_format": data.get("audio_format"),
            "subtitle_lang": data.get("subtitle_lang"),
            "output_path": download_path,
            "playlist": data.get("playlist", False),
            "sponsorblock": data.get("sponsorblock", False),
            "use_aria2c": state.config.get("use_aria2c", False),
            "gpu_accel": state.config.get("gpu_accel", "None"),
            "output_template": data.get("output_template")
            or state.config.get("output_template"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "force_generic": data.get("force_generic", False),
            "cookies_from_browser": data.get("cookies_from_browser"),
            "download_profile": data.get("download_profile"),
            "chapters": data.get("chapters", data.get("split_chapters", False)),
            "split_chapters": data.get("split_chapters", data.get("chapters", False)),
            "insta_type": data.get("insta_type"),
            "proxy": proxy,
            "rate_limit": rate_limit,
        }
        state.queue_manager.add_item(item)
        state.scheduled_time = None

        self.ui.update_queue_view()

        if status == "Queued":
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("success_added"))))

    def on_cancel_item(self, item: dict[str, Any]):
        """Callback to cancel a download item."""
        logger.info("User requested cancel for item: %s", item.get("title", "Unknown"))
        item_id = item.get("id")
        if item_id:
            state.queue_manager.cancel_item(item_id)
        else:
            item["status"] = "Cancelled"
            item["progress"] = 0
            control_ref = item.get("control_ref")
            if control_ref:
                control = control_ref()
                if control:
                    control.update_progress()

        state.queue_manager.notify_workers()

    def on_remove_item(self, item: dict[str, Any]):
        """Callback to remove an item from the queue."""
        state.queue_manager.remove_item(item)
        self.ui.update_queue_view()

    def on_reorder_item(self, item: dict[str, Any], direction: int):
        """Callback to reorder items in the queue."""
        q = state.queue_manager.get_all()
        # Find index by ID instead of object reference if possible
        idx = -1
        item_id = item.get("id")

        if item_id:
            for i, x in enumerate(q):
                if x.get("id") == item_id:
                    idx = i
                    break
        else:
            if item in q:
                # Cast item to QueueItem to satisfy mypy (TypedDict/dict compatibility)
                idx = q.index(cast(Any, item))

        if idx != -1:
            new_idx = idx + direction
            if 0 <= new_idx < len(q):
                state.queue_manager.swap_items(idx, new_idx)
                self.ui.update_queue_view()

    def on_retry_item(self, item: dict[str, Any]):
        """Callback to retry a failed/cancelled item."""
        item_id = item.get("id")
        if item_id:
            state.queue_manager.retry_item(item_id)
        self.ui.update_queue_view()

    def on_play_item(self, item: dict[str, Any]):
        """Callback to open/play the downloaded file."""
        filepath = item.get("filepath")
        if not filepath:
            output_path = item.get("output_path", get_default_download_path())
            filename = item.get("filename")
            if not filename:
                self.page.open(
                    ft.SnackBar(content=ft.Text(LM.get("file_path_unknown")))
                )
                return
            filepath = os.path.join(output_path, filename)

        if not play_file(filepath, self.page):
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("open_file_failed"))))

    def on_open_folder(self, item: dict[str, Any]):
        """Callback to open the folder containing the file."""
        output_path = item.get("output_path", get_default_download_path())
        filepath = item.get("filepath")
        if filepath and isinstance(filepath, str):
            output_path = os.path.dirname(filepath)
        if not open_folder(output_path, self.page):
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("open_folder_failed"))))

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Dispatch a picker result to the action that opened the dialog."""
        if self._picker_action == "history_export":
            self._finish_history_export(e)
            return
        if self._picker_action == "history_import":
            self._finish_history_import(e)
            return
        self.on_batch_file_result(e)

    def on_export_history(self):
        """Ask for a destination file for the history backup."""
        self._picker_action = "history_export"
        self.file_picker.save_file(
            dialog_title=LM.get("export_history"),
            file_name="streamcatch-history.json",
            allowed_extensions=["json"],
        )

    def on_import_history(self):
        """Ask for a history backup to restore."""
        self._picker_action = "history_import"
        self.file_picker.pick_files(
            dialog_title=LM.get("import_history"),
            allow_multiple=False,
            allowed_extensions=["json"],
        )

    def _finish_history_export(self, e: ft.FilePickerResultEvent):
        target = getattr(e, "path", None)
        if not target:
            return
        try:
            if not is_safe_path(target):
                raise ValueError("unsafe destination path")
            state.history_manager.export_to_json(target)
            logger.info("History exported to %s", target)
            self._show_snackbar(LM.get("history_exported"))
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("History export failed: %s", ex)
            self._show_snackbar(LM.get("history_export_failed"))

    def _finish_history_import(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        source = e.files[0].path
        try:
            if not is_safe_path(source):
                raise ValueError("unsafe source path")
            imported, skipped = state.history_manager.import_from_json_file(source)
            logger.info("History import from %s: %s imported", source, imported)
            self._show_snackbar(
                LM.get("history_imported")
                if not skipped
                else f"{LM.get('history_imported')} ({skipped} {LM.get('history_import_skipped')})"
            )
            history_view = getattr(self.ui, "history_view", None)
            if history_view is not None:
                history_view.load()
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("History import failed: %s", ex)
            self._show_snackbar(LM.get("history_import_failed"))

    def _show_snackbar(self, message: str) -> None:
        """Open a snackbar on the page when one is available."""
        try:
            self.page.open(ft.SnackBar(content=ft.Text(message)))
        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.debug("Could not show snackbar: %s", ex)

    def on_batch_file_result(self, e: ft.FilePickerResultEvent):
        """Callback when a file is selected for batch import."""
        if not e.files:
            return

        path = e.files[0].path
        try:
            count, truncated = self.batch_importer.import_from_file(path)
            self.ui.update_queue_view()

            msg = LM.get("batch_imported", count)
            if truncated:
                msg += f" {LM.get('batch_import_truncated')}"

            self.page.open(ft.SnackBar(content=ft.Text(msg)))

        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("Failed to import batch file: %s", ex, exc_info=True)
            self.page.open(
                ft.SnackBar(content=ft.Text(LM.get("batch_import_failed", str(ex))))
            )

    def on_batch_import(self):
        """Trigger batch import file picker."""
        self._picker_action = "batch_import"
        self.file_picker.pick_files(
            allow_multiple=False, allowed_extensions=["txt", "csv"]
        )

    def on_time_picked(self, e):
        """Callback when a time is picked."""
        if e.value:
            state.scheduled_time = e.value
            self.page.open(
                ft.SnackBar(
                    content=ft.Text(
                        LM.get(
                            "next_scheduled_download",
                            e.value.strftime("%H:%M"),
                        )
                    )
                )
            )

    def on_schedule(self, e):
        """Trigger schedule time picker."""
        # pylint: disable=unused-argument
        self.page.open(self.time_picker)

    def on_toggle_clipboard(self, active: bool, show_message: bool = True):
        """Callback to toggle clipboard monitor."""
        state.clipboard_monitor_active = active
        if active and not self._clipboard_monitor_started:
            self.start_clipboard_monitor()
        if show_message:
            msg = (
                LM.get("clipboard_monitor_enabled")
                if active
                else LM.get("clipboard_monitor_disabled")
            )
            self.page.open(ft.SnackBar(content=ft.Text(msg)))
