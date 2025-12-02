"""
Main application entry point.

Initializes the UI, logging, and starts the main event loop.
Refactored for event-driven queue processing and cleaner architecture.
"""

import logging
import os
import signal
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import flet as ft

from app_state import state
from clipboard_monitor import start_clipboard_monitor
from logger_config import setup_logging
from tasks import process_queue
from tasks_extended import fetch_info_task
from theme import Theme
from ui_manager import UIManager
from ui_utils import validate_url

# Setup logging immediately
setup_logging()
logger = logging.getLogger(__name__)

# Global UI Manager instance
UI: Optional[UIManager] = None
PAGE: Optional[ft.Page] = None
active_threads: list[threading.Thread] = []


@contextmanager
def startup_timeout(seconds=10):
    """Context manager for timeout on startup operations."""

    def timeout_handler(signum, frame):
        # pylint: disable=unused-argument
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    if os.name != "nt":  # signal.alarm not available on Windows
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows fallback: we can't easily interrupt the main thread.
        # Just log a warning for now as strict timeout is hard without a wrapper process.
        logger.warning("Startup timeout not enforced on Windows (platform limitation)")
        yield


# pylint: disable=too-many-locals,too-many-statements,global-statement
def main(pg: ft.Page):
    """Main application loop."""
    global PAGE, UI
    PAGE = pg

    logger.info("Initializing main UI...")

    PAGE.title = "StreamCatch - Ultimate Downloader"
    PAGE.theme_mode = ft.ThemeMode.DARK
    PAGE.padding = 0
    PAGE.window_min_width = 1100
    PAGE.window_min_height = 800
    PAGE.bgcolor = Theme.BG_DARK

    # Apply Theme
    PAGE.theme = Theme.get_theme()
    logger.debug("Theme applied.")

    # --- Pickers ---
    file_picker = ft.FilePicker()
    time_picker = ft.TimePicker(
        confirm_text="Schedule",
        error_invalid_text="Time invalid",
        help_text="Select time for download to start",
    )
    PAGE.overlay.append(file_picker)
    PAGE.overlay.append(time_picker)
    logger.debug("Pickers initialized and added to overlay.")

    # Initialize UI Manager
    UI = UIManager(PAGE)

    # --- Helpers ---

    def on_fetch_info(url):
        logger.info("User requested video info fetch for: %s", url)
        if not url:
            PAGE.open(ft.SnackBar(content=ft.Text("Please enter a URL")))
            return
        if not validate_url(url):
            PAGE.open(
                ft.SnackBar(content=ft.Text("Please enter a valid http/https URL"))
            )
            return

        if UI.download_view:
            UI.download_view.fetch_btn.disabled = True
        PAGE.update()

        logger.debug("Starting fetch_info_task thread...")
        threading.Thread(
            target=fetch_info_task, args=(url, UI.download_view, PAGE), daemon=True
        ).start()

    def get_default_download_path():
        """Get a safe default download path for the current platform."""
        try:
            # Check for Android/iOS specific (not implemented here but good to have hooks)
            home = Path.home()
            downloads = home / "Downloads"
            if downloads.exists() and os.access(downloads, os.W_OK):
                return str(downloads)
            if os.access(home, os.W_OK):
                return str(home)
        except Exception:
            pass
        return "."

    def on_add_to_queue(data):
        logger.info("User requested add to queue: %s", data.get("url"))
        if not validate_url(data.get("url", "")):
            PAGE.open(
                ft.SnackBar(content=ft.Text("Please enter a valid http/https URL"))
            )
            return

        # Rate limiting
        if not check_rate_limit():
            PAGE.open(
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
            PAGE.open(
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
            and UI.download_view
            and data["url"] == UI.download_view.url_input.value
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

        UI.update_queue_view()

        if status == "Queued":
            PAGE.open(ft.SnackBar(content=ft.Text("Added to queue")))

        # Trigger processing (redundant with Event, but harmless)
        # process_queue() # Removed, background loop handles it

    def on_cancel_item(item):
        logger.info("User requested cancel for item: %s", item.get("title", "Unknown"))
        item_id = item.get("id")
        if item_id:
            state.queue_manager.cancel_item(item_id)
        else:
            # Fallback for old items (shouldn't happen with new logic)
            item["status"] = "Cancelled"

        if "control" in item:
            item["control"].update_progress()

    def on_remove_item(item):
        state.queue_manager.remove_item(item)
        UI.update_queue_view()

    def on_reorder_item(item, direction):
        q = state.queue_manager.get_all()
        if item in q:
            idx = q.index(item)
            new_idx = idx + direction
            if 0 <= new_idx < len(q):
                state.queue_manager.swap_items(idx, new_idx)
                UI.update_queue_view()

    def on_retry_item(item):
        item["status"] = "Queued"
        item["speed"] = ""
        item["eta"] = ""
        item["size"] = ""
        item["progress"] = 0
        UI.update_queue_view()
        # Notify background loop
        try:
             with state.queue_manager._has_work:
                 state.queue_manager._has_work.notify_all()
        except Exception:
            pass

    def on_batch_file_result(e: ft.FilePickerResultEvent):
        if not e.files:
            return

        path = e.files[0].path
        try:
            with open(path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]

            max_batch = 100
            if len(urls) > max_batch:
                PAGE.open(
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

            UI.update_queue_view()
            PAGE.open(ft.SnackBar(content=ft.Text(f"Imported {count} URLs")))

        except Exception as ex:
            logger.error("Failed to import batch file: %s", ex, exc_info=True)
            PAGE.open(ft.SnackBar(content=ft.Text(f"Failed to import: {ex}")))

    def on_batch_import():
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["txt", "csv"])

    def on_time_picked(e):
        if e.value:
            state.scheduled_time = e.value
            PAGE.open(
                ft.SnackBar(
                    content=ft.Text(
                        f"Next download will be scheduled at {e.value.strftime('%H:%M')}"
                    )
                )
            )

    def on_schedule(e):
        # pylint: disable=unused-argument
        PAGE.open(time_picker)

    # Wire up pickers
    file_picker.on_result = on_batch_file_result
    time_picker.on_change = on_time_picked

    # Rate limiting
    last_add_time = [0.0]
    add_rate_limit_seconds = 0.5

    def check_rate_limit():
        import time as time_mod
        now = time_mod.time()
        if now - last_add_time[0] < add_rate_limit_seconds:
            return False
        last_add_time[0] = now
        return True

    def on_toggle_clipboard(active):
        state.clipboard_monitor_active = active
        msg = "Clipboard Monitor Enabled" if active else "Clipboard Monitor Disabled"
        PAGE.open(ft.SnackBar(content=ft.Text(msg)))

    # --- Views Initialization via UIManager ---

    main_view = UI.initialize_views(
        on_fetch_info_callback=on_fetch_info,
        on_add_to_queue_callback=on_add_to_queue,
        on_batch_import_callback=on_batch_import,
        on_schedule_callback=on_schedule,
        on_cancel_item_callback=on_cancel_item,
        on_remove_item_callback=on_remove_item,
        on_reorder_item_callback=on_reorder_item,
        on_retry_item_callback=on_retry_item,
        on_toggle_clipboard_callback=on_toggle_clipboard
    )

    PAGE.add(main_view)
    logger.info("Main view added to page.")

    # --- Background Logic ---

    def background_loop():
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

                # Check scheduled items
                if state.queue_manager.update_scheduled_items(datetime.now()) > 0:
                    UI.update_queue_view()

                # Process queue
                process_queue()

            except Exception as e:
                logger.error("Error in background_loop: %s", e, exc_info=True)
                time.sleep(1) # Prevent tight loop on error
        logger.info("Background loop stopped.")

    # Start Clipboard Monitor
    start_clipboard_monitor(PAGE, UI.download_view)

    def cleanup_on_disconnect(e):
        # pylint: disable=unused-argument
        logger.info("Page disconnected, cleaning up...")
        state.cleanup()
        for thread in active_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        logger.info("Cleanup complete")

    PAGE.on_disconnect = cleanup_on_disconnect
    PAGE.on_close = cleanup_on_disconnect

    bg_thread = threading.Thread(
        target=background_loop, daemon=True, name="BackgroundLoop"
    )
    active_threads.append(bg_thread)
    bg_thread.start()


def global_crash_handler(exctype, value, tb):
    """
    Global hook to catch ANY unhandled exception and prevent silent exit.
    """
    error_trace = "".join(traceback.format_exception(exctype, value, tb))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    crash_report = (
        f"STREAMCATCH CRASH REPORT [{timestamp}]\n"
        f"{'-'*50}\n"
        f"Type: {exctype.__name__}\n"
        f"Message: {value}\n\n"
        f"Traceback:\n{error_trace}\n"
        f"{'-'*50}\n\n"
    )

    try:
        log_path = Path.home() / ".streamcatch" / "crash.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception:
        # Fallback
        log_path = Path("crash.log")
        try:
             with open(log_path, "a", encoding="utf-8") as f:
                f.write(crash_report)
        except Exception:
            pass

    # Also write to local
    try:
        local_crash = Path("streamcatch_crash.log")
        with open(local_crash, "w", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception:
        pass

    try:
        print("\n" + "=" * 60, file=sys.stderr)
        print("CRITICAL ERROR - STREAMCATCH CRASHED", file=sys.stderr)
        print(crash_report, file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

        if os.name == "nt":
            import ctypes
            msg = f"Critical Error:\n{value}\n\nLog saved to:\n{log_path}"
            ctypes.windll.user32.MessageBoxW(0, msg, "StreamCatch Crashed", 0x10)
    except Exception:
        pass

    sys.exit(1)


if __name__ == "__main__":
    console_mode = "--console" in sys.argv or "--debug" in sys.argv
    if console_mode:
        print("Console mode enabled - all output will be visible")

    sys.excepthook = global_crash_handler

    print("=" * 60)
    print("StreamCatch Starting...")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 60 + "\n")

    try:
        with startup_timeout(30):
            try:
                logger.info("Initializing AppState...")
                _ = state  # Force singleton initialization
                logger.info("AppState initialized successfully")
            except Exception as e:
                print(f"ERROR: Failed to initialize AppState: {e}", file=sys.stderr)
                traceback.print_exc()
                sys.exit(1)

            logger.info("Starting Flet application...")
    except TimeoutError as e:
        print(f"FATAL: Startup timeout - {e}", file=sys.stderr)
        sys.exit(1)

    if os.environ.get("FLET_WEB"):
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    else:
        try:
            ft.app(target=main)
        except Exception as e:
            global_crash_handler(type(e), e, e.__traceback__)
