import logging
import threading
import time

import pyperclip

from app_state import state
from ui_utils import validate_url

logger = logging.getLogger(__name__)


def start_clipboard_monitor(page, download_view):
    """Starts the clipboard monitor thread with error handling."""
    # Test clipboard access first
    try:
        pyperclip.paste()
        logger.info("Clipboard monitoring initialized.")
    except pyperclip.PyperclipException as e:
        logger.warning(f"Clipboard access not available: {e}")
        logger.warning("Clipboard monitor will be disabled")
        return  # Don't start monitor if clipboard isn't available
    except Exception as e:
        logger.error(f"Unexpected clipboard error: {e}")
        return

    threading.Thread(
        target=_clipboard_loop, args=(page, download_view), daemon=True
    ).start()


def _clipboard_loop(page, download_view):
    """
    Background loop that checks the clipboard for URLs.
    """
    while not state.shutdown_flag.is_set():
        time.sleep(2)
        if state.clipboard_monitor_active:
            try:
                try:
                    content = pyperclip.paste()
                except pyperclip.PyperclipException:
                    # Clipboard temporarily unavailable
                    state.clipboard_monitor_active = False  # Disable permanently
                    logger.warning("Clipboard access lost, disabling monitor")
                    continue

                if content and content != state.last_clipboard_content:
                    state.last_clipboard_content = content
                    if validate_url(content) and download_view:
                        # Only auto-paste if field is empty
                        if not download_view.url_input.value:
                            logger.info(f"Clipboard URL detected: {content}")
                            download_view.url_input.value = content
                            if page:
                                import flet as ft

                                page.open(
                                    ft.SnackBar(
                                        content=ft.Text(f"URL detected: {content}")
                                    )
                                )
                                page.update()
            except Exception as e:
                # Catch-all to prevent thread death
                logger.error(f"Error in clipboard monitor: {e}", exc_info=True)
