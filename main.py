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
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import flet as ft

from app_controller import AppController
from app_state import state
from logger_config import setup_logging
from theme import Theme
from ui_manager import UIManager

# Setup logging immediately
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
UI: Optional[UIManager] = None
PAGE: Optional[ft.Page] = None
CONTROLLER: Optional[AppController] = None


@contextmanager
def startup_timeout(seconds=10):
    """Context manager for timeout on startup operations.
    Thread-based implementation compatible with Windows.
    """

    # Simple container for result/exception
    result = {"completed": False, "exception": None}

    def target(func, *args, **kwargs):
        try:
            func(*args, **kwargs)
            result["completed"] = True
        except Exception as e:
            result["exception"] = e

    # This context manager is tricky because 'yield' gives control back to caller.
    # To timeout the caller's block, we'd need to run the caller's block in a thread.
    # But usually the caller's block IS the main thread initialization.
    # On Windows, we can't interrupt the main thread easily without signals.

    # Alternative: Use a timer thread that kills the process if not cancelled?
    # That's drastic but "TimeoutError" implies we give up.

    timer = None
    timed_out = {"flag": False}
    if os.name == "nt":

        def mark_timeout():
            logger.error(
                f"Startup timed out after {seconds} seconds (Windows fallback)."
            )
            timed_out["flag"] = True

        timer = threading.Timer(seconds, mark_timeout)
        timer.daemon = True  # Ensure timer doesn't block exit
        timer.start()
        try:
            yield
        finally:
            if timer:
                timer.cancel()
            if timed_out["flag"]:
                raise TimeoutError(f"Operation timed out after {seconds} seconds")
    else:
        # Unix-like systems use signal
        def timeout_handler(signum, frame):
            # pylint: disable=unused-argument
            raise TimeoutError(f"Operation timed out after {seconds} seconds")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def main(pg: ft.Page):
    """Main application loop."""
    global PAGE, UI, CONTROLLER
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

    # Initialize UI Manager
    UI = UIManager(PAGE)

    # Initialize Controller
    CONTROLLER = AppController(PAGE, UI)

    # --- Views Initialization via UIManager ---
    # Wire callbacks to Controller methods
    main_view = UI.initialize_views(
        on_fetch_info_callback=CONTROLLER.on_fetch_info,
        on_add_to_queue_callback=CONTROLLER.on_add_to_queue,
        on_batch_import_callback=CONTROLLER.on_batch_import,
        on_schedule_callback=CONTROLLER.on_schedule,
        on_cancel_item_callback=CONTROLLER.on_cancel_item,
        on_remove_item_callback=CONTROLLER.on_remove_item,
        on_reorder_item_callback=CONTROLLER.on_reorder_item,
        on_retry_item_callback=CONTROLLER.on_retry_item,
        on_toggle_clipboard_callback=CONTROLLER.on_toggle_clipboard,
    )

    PAGE.add(main_view)
    logger.info("Main view added to page.")

    # Start Background Services
    CONTROLLER.start_background_loop()
    CONTROLLER.start_clipboard_monitor()

    def cleanup_on_disconnect(e):
        # pylint: disable=unused-argument
        logger.info("Page disconnected, cleaning up...")
        CONTROLLER.cleanup()

    PAGE.on_disconnect = cleanup_on_disconnect
    PAGE.on_close = cleanup_on_disconnect


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
    except Exception:  # pylint: disable=broad-exception-caught
        # Fallback
        log_path = Path("crash.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(crash_report)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    # Also write to local
    try:
        local_crash = Path("streamcatch_crash.log")
        with open(local_crash, "w", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    try:
        print("\n" + "=" * 60, file=sys.stderr)
        print("CRITICAL ERROR - STREAMCATCH CRASHED", file=sys.stderr)
        print(crash_report, file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

        if os.name == "nt":
            # Only show message box if we have a UI or are not headless?
            # We can't easily detect headless, but we can try catch
            try:
                import ctypes  # pylint: disable=import-outside-toplevel

                msg = f"Critical Error:\n{value}\n\nLog saved to:\n{log_path}"
                ctypes.windll.user32.MessageBoxW(0, msg, "StreamCatch Crashed", 0x10)
            except Exception:
                pass
    except Exception:  # pylint: disable=broad-exception-caught
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
