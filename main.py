"""
Main application entry point.

Initializes the UI, logging, and starts the main event loop.
Refactored for event-driven queue processing and cleaner architecture.
"""

import logging
import os
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import flet as ft

from app_controller import AppController
from app_state import state
from localization_manager import LocalizationManager as LM
from logger_config import setup_logging
from theme import Theme
from ui_manager import UIManager

# Setup logging immediately
setup_logging()
logger = logging.getLogger(__name__)

__version__ = "2.0.0"

# Global instances
# pylint: disable=invalid-name
UI: UIManager | None = None
PAGE: ft.Page | None = None
CONTROLLER: AppController | None = None


def _handle_signal(sig: int, frame: Any) -> None:
    """Handle interrupt signals for graceful shutdown."""
    # pylint: disable=unused-argument
    logger.info("Received signal %s, initiating graceful shutdown...", sig)
    if CONTROLLER:
        CONTROLLER.cleanup()
    sys.exit(0)


def main(pg: ft.Page) -> None:
    """Main application loop."""
    # pylint: disable=global-statement
    global PAGE, UI, CONTROLLER
    PAGE = pg

    try:
        logger.info("Initializing main UI...")

        # 1. Load localization before creating any UI controls
        # Ensure state.config is loaded by accessing state
        LM.load_language(state.config.get("language", "en"))

        PAGE.title = LM.get("app_title", "StreamCatch - Ultimate Downloader")

        # 2. Load Theme Mode from Config
        theme_mode_str = str(state.config.get("theme_mode", "dark")).lower()
        if theme_mode_str == "light":
            PAGE.theme_mode = ft.ThemeMode.LIGHT
        elif theme_mode_str == "system":
            PAGE.theme_mode = ft.ThemeMode.SYSTEM
        else:
            PAGE.theme_mode = ft.ThemeMode.DARK

        PAGE.padding = 0
        PAGE.window_min_width = 1100
        PAGE.window_min_height = 800
        PAGE.bgcolor = Theme.BG_DARK

        # 3. Apply Theme
        if state.high_contrast:
            PAGE.theme = Theme.get_high_contrast_theme()
        else:
            PAGE.theme = Theme.get_theme()
        logger.debug("Theme applied.")

        # 4. Keyboard Handling
        def on_keyboard(e: ft.KeyboardEvent) -> None:
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

        # 5. Initialize UI Manager
        UI = UIManager(PAGE)

        # 6. Initialize Controller
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

        # 7. Start Background Services
        CONTROLLER.start_background_loop()
        if state.clipboard_monitor_active:
            CONTROLLER.start_clipboard_monitor()

        def cleanup_on_disconnect(e: Any) -> None:
            # pylint: disable=unused-argument
            logger.info("Page disconnected, cleaning up...")
            if CONTROLLER:
                CONTROLLER.cleanup()

        PAGE.on_disconnect = cleanup_on_disconnect
        PAGE.on_close = cleanup_on_disconnect

    except Exception as e:
        logger.critical("Failed to initialize main application: %s", e, exc_info=True)
        # We could show a simple error text on page if Flet is partially alive
        try:
            PAGE.clean()
            PAGE.add(ft.Text(f"Critical Startup Error:\n{e}", color="red", size=20))
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        raise


def global_crash_handler(exctype: type, value: BaseException, tb: Any) -> None:
    """
    Global hook to catch ANY unhandled exception and prevent silent exit.
    Recursively dumps locals (sanitized) if possible.
    """
    error_trace = "".join(traceback.format_exception(exctype, value, tb))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Basic local var dump (sanitized)
    locals_dump = ""
    try:
        # Walk stack
        stack = traceback.extract_tb(tb)
        if stack:
            # Get last frame
            # (Note: standard traceback objects don't easily give access to frame locals without 'inspect')
            # pylint: disable=unused-import
            import inspect

            if tb:
                last_trace = tb
                while last_trace.tb_next:
                    last_trace = last_trace.tb_next
                frame = last_trace.tb_frame
                locals_dump = "\nLocals in last frame:\n"
                for k, v in frame.f_locals.items():
                    # Sanitize sensitive keys
                    if any(
                        s in k.lower()
                        for s in ["key", "token", "password", "secret", "auth"]
                    ):
                        v = "***REDACTED***"
                    try:
                        v_str = str(v)[:500]  # Truncate
                    except Exception:  # pylint: disable=broad-exception-caught
                        v_str = "<unprintable>"
                    locals_dump += f"  {k} = {v_str}\n"
    except Exception as dump_exc:  # pylint: disable=broad-exception-caught
        locals_dump = f"\nFailed to dump locals: {dump_exc}\n"

    crash_report = (
        f"STREAMCATCH CRASH REPORT [{timestamp}]\n"
        f"{'-'*50}\n"
        f"Type: {exctype.__name__}\n"
        f"Message: {value}\n\n"
        f"Traceback:\n{error_trace}\n"
        f"{locals_dump}\n"
        f"{'-'*50}\n\n"
    )

    try:
        log_path = Path.home() / ".streamcatch" / "crash.log"
        if not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
        # Write crash log with secure permissions
        with open(
            log_path, "a", encoding="utf-8", opener=lambda p, f: os.open(p, f, 0o600)
        ) as f:
            f.write(crash_report)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to write crash log in user directory: %s", exc)
        # Fallback
        log_path = Path("crash.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(crash_report)
        except Exception as fallback_exc:  # pylint: disable=broad-exception-caught
            logger.error("Failed to write fallback crash log: %s", fallback_exc)

    try:
        logger.critical("%s", "\n" + "=" * 60)
        logger.critical("%s", "CRITICAL ERROR - STREAMCATCH CRASHED")
        logger.critical("%s", crash_report)
        logger.critical("%s", "=" * 60 + "\n")

        if os.name == "nt":
            try:
                import ctypes  # pylint: disable=import-outside-toplevel

                msg = f"Critical Error:\n{value}\n\nLog saved to:\n{log_path}"
                if hasattr(ctypes, "windll"):
                    ctypes.windll.user32.MessageBoxW(0, msg, "StreamCatch Crashed", 0x10)
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

    # Register signal handlers
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("%s", "=" * 60)
    logger.info("%s", "StreamCatch Starting...")
    logger.info("Python: %s", sys.version)
    logger.info("Working Directory: %s", os.getcwd())
    logger.info("%s", "=" * 60 + "\n")

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
