"""
Main application entry point.

Initializes the UI, logging, and starts the main event loop.
"""

import logging
import logging.handlers
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

from app_layout import AppLayout
from app_state import state
from clipboard_monitor import start_clipboard_monitor
from tasks import process_queue
from tasks_extended import fetch_info_task
from theme import Theme
from ui_utils import validate_url
from views.dashboard_view import DashboardView
from views.download_view import DownloadView
from views.history_view import HistoryView
from views.queue_view import QueueView
from views.rss_view import RSSView
from views.settings_view import SettingsView


# Configure logging
def setup_logging():
    """Setup comprehensive logging configuration."""
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers to prevent duplication
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Console Handler (INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # File Handler (DEBUG+, Rotating)
    # Log to both local directory (for easy access) and user home (persistence)
    # Use fallback if home is not writable (mobile/sandbox)
    home_log = Path.home() / ".streamcatch" / "app.log"
    try:
        home_log.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to local
        home_log = Path("app.log")

    log_files = [Path("ytdownloader.log"), home_log]

    # Deduplicate paths if home == local
    log_files = list(set(log_files))

    for log_file in log_files:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(log_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup log file {log_file}: {e}", file=sys.stderr)

    logging.info("Logging initialized successfully.")


setup_logging()
logger = logging.getLogger(__name__)

# Module-level handles primarily for tests and integrations
DOWNLOAD_VIEW: Optional[DownloadView] = None
QUEUE_VIEW: Optional[QueueView] = None
PAGE: Optional[ft.Page] = None
active_threads: list[threading.Thread] = []  # Track all created threads


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
        # Windows: usage of threading.Timer to simulate timeout for the block
        # However, we can't easily interrupt the main thread from a timer thread
        # without raising an exception in it (which is tricky in Python).
        # We will use a simpler approach: Just yield.
        # Implementing strict timeout on Windows for main thread operations is complex
        # and might be overkill if we just want to avoid hanging forever.
        # Ideally, we should run startup tasks in a thread with timeout, but that requires
        # restructuring main(). For now, we keep as is but log_warning.
        logger.warning("Startup timeout not enforced on Windows")
        yield


# pylint: disable=too-many-locals,too-many-statements,global-statement
def main(pg: ft.Page):
    """Main application loop."""
    global PAGE, DOWNLOAD_VIEW, QUEUE_VIEW
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

    # --- Helpers ---

    def on_fetch_info(url):
        logger.info("User requested video info fetch for: %s", url)
        if not url:
            logger.debug("Fetch ignored: URL is empty")
            PAGE.open(ft.SnackBar(content=ft.Text("Please enter a URL")))
            return
        if not validate_url(url):
            logger.warning("Fetch ignored: Invalid URL format: %s", url)
            PAGE.open(
                ft.SnackBar(content=ft.Text("Please enter a valid http/https URL"))
            )
            return

        if DOWNLOAD_VIEW:
            DOWNLOAD_VIEW.fetch_btn.disabled = True
        PAGE.update()

        logger.debug("Starting fetch_info_task thread...")
        threading.Thread(
            target=fetch_info_task, args=(url, DOWNLOAD_VIEW, PAGE), daemon=True
        ).start()

    def get_default_download_path():
        """Get a safe default download path for the current platform."""
        try:
            home = Path.home()
            downloads = home / "Downloads"
            # Check if downloads directory exists/is accessible
            if downloads.exists() and os.access(downloads, os.W_OK):
                return str(downloads)

            # Fallback to home if writable
            if os.access(home, os.W_OK):
                return str(home)
        except Exception:
            pass

        # Fallback to current directory (app sandbox/local)
        return "."

    def on_add_to_queue(data):
        logger.info("User requested add to queue: %s", data.get("url"))
        # Process data and add to queue
        if not validate_url(data.get("url", "")):
            logger.warning("Invalid URL rejected: %s", data.get("url"))
            PAGE.open(
                ft.SnackBar(content=ft.Text("Please enter a valid http/https URL"))
            )
            return

        # Rate limiting
        if not check_rate_limit():
            logger.debug("Rate limit hit for adding to queue")
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
            # Combine current date with scheduled time
            sched_dt = datetime.combine(now.date(), state.scheduled_time)
            # If time is in the past for today, schedule for tomorrow
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
            logger.info("Item scheduled for %s", sched_dt)

        # Safely handle potential missing state.video_info or mismatch
        title = data["url"]
        video_info = state.get_video_info(data["url"])
        if video_info:
            title = video_info.get("title", data["url"])
        elif (
            state.video_info
            and DOWNLOAD_VIEW
            and data["url"] == DOWNLOAD_VIEW.url_input.value
        ):
            title = state.video_info.get("title", data["url"])

        logger.debug("Resolved title for queue item: %s", title)

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
        if QUEUE_VIEW:
            QUEUE_VIEW.rebuild()
        if status == "Queued":
            PAGE.open(ft.SnackBar(content=ft.Text("Added to queue")))
        process_queue()

    def on_cancel_item(item):
        logger.info("User requested cancel for item: %s", item.get("title", "Unknown"))
        item["status"] = "Cancelled"
        if state.current_download_item == item and state.cancel_token:
            logger.info("Triggering cancel_token for active download")
            state.cancel_token.cancel()
        if "control" in item:
            item["control"].update_progress()

    def on_remove_item(item):
        logger.info("Removing item from queue UI: %s", item.get("title", "Unknown"))
        state.queue_manager.remove_item(item)
        if QUEUE_VIEW:
            QUEUE_VIEW.rebuild()

    def on_reorder_item(item, direction):
        q = state.queue_manager.get_all()
        if item in q:
            idx = q.index(item)
            new_idx = idx + direction
            if 0 <= new_idx < len(q):
                logger.debug("Reordering item %d -> %d", idx, new_idx)
                state.queue_manager.swap_items(idx, new_idx)
                if QUEUE_VIEW:
                    QUEUE_VIEW.rebuild()

    def on_retry_item(item):
        logger.info("Retrying item: %s", item.get("title", "Unknown"))
        # Logic to retry download
        item["status"] = "Queued"
        item["speed"] = ""
        item["eta"] = ""
        item["size"] = ""
        if QUEUE_VIEW:
            QUEUE_VIEW.rebuild()
        process_queue()

    def on_batch_file_result(e: ft.FilePickerResultEvent):
        if not e.files:
            logger.debug("Batch import cancelled by user")
            return

        path = e.files[0].path
        logger.info("Processing batch file: %s", path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]

            # Limit batch import size
            max_batch = 100
            if len(urls) > max_batch:
                logger.warning(
                    "Batch file too large (%d), limiting to %d", len(urls), max_batch
                )
                PAGE.open(
                    ft.SnackBar(
                        content=ft.Text(
                            f"Batch import limited to {max_batch} URLs. Imported first {max_batch}."
                        )
                    )
                )
                urls = urls[:max_batch]

            count = 0
            # Get safe download path once
            dl_path = get_default_download_path()

            for url in urls:
                if not url:
                    continue
                # Add basic item
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

            if QUEUE_VIEW:
                QUEUE_VIEW.rebuild()
            logger.info("Batch import completed: %d URLs added", count)
            PAGE.open(ft.SnackBar(content=ft.Text(f"Imported {count} URLs")))
            process_queue()

        except Exception as ex:  # pylint: disable=broad-exception-caught
            logger.error("Failed to import batch file: %s", ex, exc_info=True)
            PAGE.open(ft.SnackBar(content=ft.Text(f"Failed to import: {ex}")))

    def on_batch_import():
        logger.debug("Opening file picker for batch import")
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["txt", "csv"])

    def on_time_picked(e):
        if e.value:
            state.scheduled_time = e.value
            logger.info("Scheduled time set to: %s", e.value)
            PAGE.open(
                ft.SnackBar(
                    content=ft.Text(
                        f"Next download will be scheduled at {e.value.strftime('%H:%M')}"
                    )
                )
            )

    def on_schedule(e):
        # pylint: disable=unused-argument
        logger.debug("Opening time picker for scheduling")
        PAGE.open(time_picker)

    # Wire up pickers
    file_picker.on_result = on_batch_file_result
    time_picker.on_change = on_time_picked

    # Rate limiting for queue additions
    last_add_time = [0.0]  # Mutable to allow modification in closure
    add_rate_limit_seconds = 0.5  # Minimum 0.5s between adds

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
        logger.info(msg)
        PAGE.open(ft.SnackBar(content=ft.Text(msg)))

    # --- Views Initialization ---
    logger.debug("Initializing DownloadView...")
    DOWNLOAD_VIEW = DownloadView(
        on_fetch_info, on_add_to_queue, on_batch_import, on_schedule, state
    )
    logger.debug("Initializing QueueView...")
    QUEUE_VIEW = QueueView(
        state.queue_manager, on_cancel_item, on_remove_item, on_reorder_item
    )
    QUEUE_VIEW.on_retry = on_retry_item

    logger.debug("Initializing HistoryView...")
    history_view = HistoryView()
    logger.debug("Initializing DashboardView...")
    dashboard_view = DashboardView()
    logger.debug("Initializing RSSView...")
    rss_view = RSSView(state.config)
    logger.debug("Initializing SettingsView...")
    settings_view = SettingsView(state.config)

    views_list = [
        DOWNLOAD_VIEW,
        QUEUE_VIEW,
        history_view,
        dashboard_view,
        rss_view,
        settings_view,
    ]

    # --- Navigation ---

    def navigate_to(index):
        logger.debug("Navigating to view index: %d", index)
        app_layout.set_content(views_list[index])
        if index == 2:
            history_view.load()
        elif index == 3:
            dashboard_view.load()
        elif index == 4:
            rss_view.load()
        PAGE.update()

    app_layout = AppLayout(
        PAGE,
        navigate_to,
        on_toggle_clipboard,
        state.clipboard_monitor_active,
        initial_view=DOWNLOAD_VIEW,
    )

    # Initial View
    PAGE.add(app_layout.view)
    logger.info("Main view added to page.")

    # --- Background Logic ---

    def background_loop():
        """Background loop for queue processing."""
        logger.info("Background loop started.")
        while not state.shutdown_flag.is_set():
            time.sleep(2)
            try:
                process_queue()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error in process_queue: %s", e, exc_info=True)
        logger.info("Background loop stopped.")

    # Start Clipboard Monitor (it runs its own loop)
    start_clipboard_monitor(PAGE, DOWNLOAD_VIEW)

    def cleanup_on_disconnect(e):
        # pylint: disable=unused-argument
        """Cleanup function when page disconnects."""
        logger.info("Page disconnected, cleaning up...")
        state.cleanup()

        # Wait for threads to finish (with timeout)
        for thread in active_threads:
            if thread.is_alive():
                logger.debug("Waiting for thread %s to finish...", thread.name)
                thread.join(timeout=2.0)

        logger.info("Cleanup complete")

    PAGE.on_disconnect = cleanup_on_disconnect
    PAGE.on_close = cleanup_on_disconnect  # Also handle close event explicitly

    bg_thread = threading.Thread(
        target=background_loop, daemon=True, name="BackgroundLoop"
    )
    active_threads.append(bg_thread)
    bg_thread.start()


def global_crash_handler(exctype, value, tb):
    """
    Global hook to catch ANY unhandled exception and prevent silent exit.
    Writes a crash log to ~/.streamcatch/crash.log and, on Windows,
    shows a native MessageBox.
    """
    # Build crash report
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

    # Persist to disk
    try:
        log_path = Path.home() / ".streamcatch" / "crash.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception:
        # Fallback log path if home not accessible
        log_path = Path("crash.log")
        try:
             with open(log_path, "a", encoding="utf-8") as f:
                f.write(crash_report)
        except Exception:
            pass

    # ALSO write to current directory for visibility
    try:
        local_crash = Path("streamcatch_crash.log")
        with open(local_crash, "w", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception:
        pass

    # Surface to user
    try:
        # Always write to stderr first
        print("\n" + "=" * 60, file=sys.stderr)
        print("CRITICAL ERROR - STREAMCATCH CRASHED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(crash_report, file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

        msg = f"Critical Error:\n{value}\n\nLog saved to:\n{log_path}"
        if os.name == "nt":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0, msg, "StreamCatch Crashed", 0x10  # MB_ICONERROR
            )
        else:
            # For Linux/macOS, at least print to stderr
            print(crash_report, file=sys.stderr)
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    # Check for console mode flag
    console_mode = "--console" in sys.argv or "--debug" in sys.argv
    if console_mode:
        print("Console mode enabled - all output will be visible")

    # Install global crash handler for any uncaught exceptions
    sys.excepthook = global_crash_handler

    # Startup diagnostics
    print("=" * 60)
    print("StreamCatch Starting...")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Executable: {sys.executable}")
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    print(f"Arguments: {sys.argv}")
    print("=" * 60 + "\n")

    try:
        # Wrap startup in timeout
        with startup_timeout(30):
            # Pre-initialize critical components with error handling
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
        except Exception as e:  # Fallback if Flet fails to start
            global_crash_handler(type(e), e, e.__traceback__)
