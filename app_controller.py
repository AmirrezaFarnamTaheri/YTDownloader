"""
AppController module.
Handles application logic, callbacks, and bridging between UI and backend.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

import flet as ft

from app_state import state
from clipboard_monitor import start_clipboard_monitor
from tasks import process_queue
from tasks_extended import fetch_info_task
from ui_manager import UIManager
from ui_utils import validate_url, get_default_download_path

logger = logging.getLogger(__name__)


class AppController:
    """
    Controller for the main application.
    Manages interactions between the UI (View) and the Backend (Model/Logic).
    """

    def __init__(self, page: ft.Page, ui_manager: UIManager):
        self.page = page
        self.ui = ui_manager
        self.active_threads: list[threading.Thread] = []
        self._last_add_time = [0.0]
        self._add_rate_limit_seconds = 0.5

        # Initialize Pickers
        self.file_picker = ft.FilePicker()
        self.time_picker = ft.TimePicker(
            confirm_text="Schedule",
            error_invalid_text="Time invalid",
            help_text="Select time for download to start",
        )
        self.page.overlay.append(self.file_picker)
        self.page.overlay.append(self.time_picker)

        # Wire up pickers
        self.file_picker.on_result = self.on_batch_file_result
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
            start_clipboard_monitor(self.page, self.ui.download_view)

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
        Waits for signals from QueueManager instead of busy-waiting.
        """
        logger.info("Background loop started.")
        while not state.shutdown_flag.is_set():
            try:
                # Wait for work or timeout (to check shutdown flag)
                # wait_for_items returns True if notified, False if timeout
                state.queue_manager.wait_for_items(timeout=2.0)

                # Check shutdown immediately after wake
                if state.shutdown_flag.is_set():
                    break

                # Check scheduled items
                if state.queue_manager.update_scheduled_items(datetime.now()) > 0:
                    self.ui.update_queue_view()

                # Process queue
                process_queue()

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error in background_loop: %s", e, exc_info=True)
                time.sleep(1)  # Prevent tight loop on error
        logger.info("Background loop stopped.")

    # --- Callbacks ---

    def on_fetch_info(self, url: str):
        """Callback to fetch video information."""
        logger.info("User requested video info fetch for: %s", url)
        if not url:
            self.page.open(ft.SnackBar(content=ft.Text("Please enter a URL")))
            return
        if not validate_url(url):
            self.page.open(
                ft.SnackBar(content=ft.Text("Please enter a valid http/https URL"))
            )
            return

        if self.ui.download_view:
            self.ui.download_view.fetch_btn.disabled = True
        self.page.update()

        logger.debug("Starting fetch_info_task thread...")
        threading.Thread(
            target=fetch_info_task,
            args=(url, self.ui.download_view, self.page),
            daemon=True,
        ).start()

    def on_add_to_queue(self, data: Dict[str, Any]):
        """Callback to add an item to the download queue."""
        logger.info("User requested add to queue: %s", data.get("url"))
        if not validate_url(data.get("url", "")):
            self.page.open(
                ft.SnackBar(content=ft.Text("Please enter a valid http/https URL"))
            )
            return

        # Rate limiting
        if not self._check_rate_limit():
            self.page.open(
                ft.SnackBar(
                    content=ft.Text("Please wait before adding another download")
                )
            )
            return

        status = "Queued"
        sched_dt = None

        if state.scheduled_time:
            now = datetime.now()
            sched_dt = datetime.combine(now.date(), state.scheduled_time)
            if sched_dt < now:
                sched_dt += timedelta(days=1)
            status = f"Scheduled ({sched_dt.strftime('%H:%M')})"
            self.page.open(
                ft.SnackBar(
                    content=ft.Text(
                        f"Download scheduled for {sched_dt.strftime('%Y-%m-%d %H:%M')}"
                    )
                )
            )

        title = data["url"]
        video_info = state.get_video_info(data["url"])
        if video_info:
            title = video_info.get("title", data["url"])
        elif (
            state.video_info
            and self.ui.download_view
            and data["url"] == self.ui.download_view.url_input.value
        ):
            title = state.video_info.get("title", data["url"])

        item = {
            "url": data["url"],
            "title": title,
            "status": status,
            "scheduled_time": sched_dt,
            "video_format": data["video_format"],
            "output_path": get_default_download_path(),
            "playlist": data["playlist"],
            "sponsorblock": data["sponsorblock"],
            "use_aria2c": state.config.get("use_aria2c", False),
            "gpu_accel": state.config.get("gpu_accel", "None"),
            "output_template": data["output_template"],
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "force_generic": data["force_generic"],
            "cookies_from_browser": data.get("cookies_from_browser"),
        }
        state.queue_manager.add_item(item)
        state.scheduled_time = None

        self.ui.update_queue_view()

        if status == "Queued":
            self.page.open(ft.SnackBar(content=ft.Text("Added to queue")))

    def on_cancel_item(self, item: Dict[str, Any]):
        """Callback to cancel a download item."""
        logger.info("User requested cancel for item: %s", item.get("title", "Unknown"))
        item_id = item.get("id")
        if item_id:
            state.queue_manager.cancel_item(item_id)
        else:
            # Fallback for old items (shouldn't happen with new logic)
            item["status"] = "Cancelled"
            item["progress"] = 0
            item["speed"] = ""
            item["eta"] = ""
            item["size"] = ""

        if "control" in item:
            item["control"].update_progress()

        state.queue_manager.notify_workers()

    def on_remove_item(self, item: Dict[str, Any]):
        """Callback to remove an item from the queue."""
        state.queue_manager.remove_item(item)
        self.ui.update_queue_view()

    def on_reorder_item(self, item: Dict[str, Any], direction: int):
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
                idx = q.index(item)

        if idx != -1:
            new_idx = idx + direction
            if 0 <= new_idx < len(q):
                state.queue_manager.swap_items(idx, new_idx)
                self.ui.update_queue_view()

    def on_retry_item(self, item: Dict[str, Any]):
        """Callback to retry a failed/cancelled item."""
        item_id = item.get("id")
        if not item_id:
            # Fallback for older items without an ID
            item["status"] = "Queued"
            item["speed"] = ""
            item["eta"] = ""
            item["size"] = ""
            item["progress"] = 0
        else:
            # Use the new QueueManager method to handle the update atomically
            state.queue_manager.update_item_status(
                item_id,
                "Queued",
                updates={"speed": "", "eta": "", "size": "", "progress": 0},
            )

        self.ui.update_queue_view()

    def on_batch_file_result(self, e: ft.FilePickerResultEvent):
        """Callback when a file is selected for batch import."""
        if not e.files:
            return

        path = e.files[0].path
        try:
            with open(path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]

            max_batch = 100
            if len(urls) > max_batch:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(
                            f"Batch import limited to {max_batch} URLs. Imported first {max_batch}."
                        )
                    )
                )
                urls = urls[:max_batch]

            dl_path = get_default_download_path()
            count = 0
            for url in urls:
                if not url:
                    continue
                item = {
                    "url": url,
                    "title": url,
                    "status": "Queued",
                    "scheduled_time": None,
                    "video_format": "best",
                    "output_path": dl_path,
                    "playlist": False,
                    "sponsorblock": False,
                    "use_aria2c": state.config.get("use_aria2c", False),
                    "gpu_accel": state.config.get("gpu_accel", "None"),
                    "output_template": "%(title)s.%(ext)s",
                    "start_time": None,
                    "end_time": None,
                    "force_generic": False,
                    "cookies_from_browser": None,
                }
                state.queue_manager.add_item(item)
                count += 1

            self.ui.update_queue_view()
            self.page.open(ft.SnackBar(content=ft.Text(f"Imported {count} URLs")))

        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("Failed to import batch file: %s", ex, exc_info=True)
            self.page.open(ft.SnackBar(content=ft.Text(f"Failed to import: {ex}")))

    def on_batch_import(self):
        """Trigger batch import file picker."""
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
                        f"Next download will be scheduled at {e.value.strftime('%H:%M')}"
                    )
                )
            )

    def on_schedule(self, e):
        """Trigger schedule time picker."""
        # pylint: disable=unused-argument
        self.page.open(self.time_picker)

    def on_toggle_clipboard(self, active: bool):
        """Callback to toggle clipboard monitor."""
        state.clipboard_monitor_active = active
        msg = "Clipboard Monitor Enabled" if active else "Clipboard Monitor Disabled"
        self.page.open(ft.SnackBar(content=ft.Text(msg)))

    def _check_rate_limit(self) -> bool:
        """Check if enough time has passed since the last add operation."""
        now = time.time()
        if now - self._last_add_time[0] < self._add_rate_limit_seconds:
            return False
        self._last_add_time[0] = now
        return True
