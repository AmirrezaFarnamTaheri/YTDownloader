"""
Main application entry point.

Initializes the UI, logging, and starts the main event loop.
Refactored for event-driven queue processing and cleaner architecture.
"""

import logging
import os
import sys
import traceback
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


def main(pg: ft.Page):
    """Main application loop."""
    # pylint: disable=global-statement
    global PAGE, UI, CONTROLLER
    PAGE = pg

    logger.info("Initializing main UI...")

    PAGE.title = "StreamCatch - Ultimate Downloader"

    # Load Theme Mode from Config
    theme_mode_str = state.config.get("theme_mode", "dark").lower()
    PAGE.theme_mode = (
        ft.ThemeMode.LIGHT if theme_mode_str == "light" else ft.ThemeMode.DARK
    )

    PAGE.padding = 0
    PAGE.window_min_width = 1100
    PAGE.window_min_height = 800
    PAGE.bgcolor = Theme.BG_DARK

    # Apply Theme
    if state.high_contrast:
        PAGE.theme = Theme.get_high_contrast_theme()
    else:
        PAGE.theme = Theme.get_theme()
    logger.debug("Theme applied.")

    # Keyboard Handling
    def on_keyboard(e: ft.KeyboardEvent):
        if not UI or not UI.queue_view:
            return

        # J / K Navigation
        if e.key == "J":  # Next
            idx = UI.queue_view.selected_index + 1
            UI.queue_view.select_item(idx)
        elif e.key == "K":  # Prev
            idx = UI.queue_view.selected_index - 1
            UI.queue_view.select_item(idx)

        # Delete
        elif e.key == "Delete":
            item = UI.queue_view.get_selected_item()
            if item and CONTROLLER:
                CONTROLLER.on_remove_item(item)
                # Ideally we move selection up one.
                UI.queue_view.select_item(UI.queue_view.selected_index)

    PAGE.on_keyboard_event = on_keyboard  # type: ignore

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
        on_play_callback=CONTROLLER.on_play_item,
        on_open_folder_callback=CONTROLLER.on_open_folder,
    )

    PAGE.add(main_view)
    logger.info("Main view added to page.")

    # Start Background Services
    CONTROLLER.start_background_loop()
    CONTROLLER.start_clipboard_monitor()

    def cleanup_on_disconnect(e):
        # pylint: disable=unused-argument
        logger.info("Page disconnected, cleaning up...")
        if CONTROLLER:
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
        # Write crash log with secure permissions
        with open(
            log_path, "a", encoding="utf-8", opener=lambda p, f: os.open(p, f, 0o600)
        ) as f:
            f.write(crash_report)
        # Ensure permissions are set
        try:
            os.chmod(log_path, 0o600)
        except OSError:
            pass
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
        logger.critical("\n" + "=" * 60)
        logger.critical("CRITICAL ERROR - STREAMCATCH CRASHED")
        logger.critical(crash_report)
        logger.critical("=" * 60 + "\n")

        if os.name == "nt":
            # Try to show message box in a separate thread to avoid blocking if possible,
            # but here we are crashing anyway.
            try:
                import ctypes  # pylint: disable=import-outside-toplevel

                # MessageBoxW blocks, but since we are crashing, it's fine.
                msg = f"Critical Error:\n{value}\n\nLog saved to:\n{log_path}"
                ctypes.windll.user32.MessageBoxW(0, msg, "StreamCatch Crashed", 0x10)
            except OSError:
                pass
            except Exception:  # pylint: disable=broad-exception-caught
                pass
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    sys.exit(1)


if __name__ == "__main__":
    console_mode = "--console" in sys.argv or "--debug" in sys.argv
    if console_mode:
        logger.info("Console mode enabled - all output will be visible")

    sys.excepthook = global_crash_handler

    logger.info("=" * 60)
    logger.info("StreamCatch Starting...")
    logger.info("Python: %s", sys.version)
    logger.info("Working Directory: %s", os.getcwd())
    logger.info("=" * 60 + "\n")

    try:
        # Initialize AppState first to fail fast if config/DB is broken
        logger.info("Initializing AppState...")
        # Accessing state triggers initialization
        _ = state
        logger.info("AppState initialized successfully")
    # pylint: disable=broad-exception-caught
    except Exception as e:
        # pylint: disable=broad-exception-caught
        print(f"ERROR: Failed to initialize AppState: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    if os.environ.get("FLET_WEB"):
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    else:
        try:
            ft.app(target=main)
        except Exception as e:  # pylint: disable=broad-exception-caught
            global_crash_handler(type(e), e, e.__traceback__)
