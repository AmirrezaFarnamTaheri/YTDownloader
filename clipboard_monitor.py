"""
Clipboard monitor module.

Monitors the system clipboard for URLs and automatically populates the download field.
"""

import logging
import threading
import time

import pyperclip

from app_state import state
from localization_manager import LocalizationManager as LM
from ui_utils import validate_url

# Lock for clipboard state access
_clipboard_state_lock = threading.Lock()
_monitor_lock = threading.Lock()
_monitor_thread = None

logger = logging.getLogger(__name__)


def start_clipboard_monitor(page, download_view):
    """Starts the clipboard monitor thread with error handling."""
    global _monitor_thread

    # Thread-safe check and assignment
    with _monitor_lock:
        if _monitor_thread and _monitor_thread.is_alive():
            logger.debug("Clipboard monitor already running.")
            return True

        # Test clipboard access first
        try:
            pyperclip.paste()
            logger.info("Clipboard monitoring initialized.")
        except pyperclip.PyperclipException as e:
            logger.warning("Clipboard access not available: %s", e)
            logger.warning("Clipboard monitor will be disabled")
            return False  # Don't start monitor if clipboard isn't available
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Unexpected clipboard error: %s", e)
            return False

        thread = threading.Thread(
            target=_clipboard_loop, args=(page, download_view), daemon=True
        )
        _monitor_thread = thread
        thread.start()
        logger.info("Clipboard monitor thread started.")
        return True


def _clipboard_loop(page, download_view):
    """
    Background loop that checks the clipboard for URLs.
    Implements adaptive polling to save resources.
    """
    # pylint: disable=import-outside-toplevel
    import flet as ft

    poll_interval = 1.0
    max_interval = 5.0

    while not state.shutdown_flag.is_set():
        time.sleep(poll_interval)

        if state.clipboard_monitor_active:
            try:
                try:
                    content = pyperclip.paste()
                except pyperclip.PyperclipException:
                    # Clipboard temporarily unavailable - thread-safe disable
                    with _clipboard_state_lock:
                        state.clipboard_monitor_active = False  # Disable permanently
                    logger.warning("Clipboard access lost, disabling monitor")
                    continue

                should_process = False
                with _clipboard_state_lock:
                    if content and content != state.last_clipboard_content:
                        state.last_clipboard_content = content
                        should_process = True
                        # Reset polling interval on activity
                        poll_interval = 1.0
                    else:
                        # Adaptive polling: increase interval if idle
                        poll_interval = min(poll_interval + 0.5, max_interval)

                if should_process:
                    if validate_url(content) and download_view and page:
                        logger.info("Clipboard URL detected: %s", content)
                        detected_url = content  # Capture value for closure

                        # UI updates must be thread-safe - use page's event loop
                        def update_ui(url=detected_url):
                            try:
                                # Check if field is empty and update it (thread-safe)
                                if not download_view.url_input.value:
                                    download_view.url_input.value = url
                                    page.open(
                                        ft.SnackBar(
                                            content=ft.Text(
                                                LM.get("clipboard_url_detected", url)
                                            )
                                        )
                                    )
                                    download_view.update()
                            except Exception as ex:
                                logger.warning(
                                    "Failed to update UI from clipboard: %s",
                                    ex,
                                )

                        # Schedule UI update on page's thread
                        try:
                            page.run_task(update_ui)
                        except AttributeError:
                            # Fallback for older Flet versions without run_task
                            update_ui()

            except Exception as e:  # pylint: disable=broad-exception-caught
                # Catch-all to prevent thread death
                logger.error("Error in clipboard monitor: %s", e, exc_info=True)
                # If we error, back off a bit
                time.sleep(2)
