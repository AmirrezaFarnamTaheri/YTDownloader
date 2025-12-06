"""
Clipboard monitor module.

Monitors the system clipboard for URLs and automatically populates the download field.
"""

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
        logger.warning("Clipboard access not available: %s", e)
        logger.warning("Clipboard monitor will be disabled")
        return  # Don't start monitor if clipboard isn't available
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Unexpected clipboard error: %s", e)
        return

    threading.Thread(
        target=_clipboard_loop, args=(page, download_view), daemon=True
    ).start()


def _clipboard_loop(page, download_view):
    """
    Background loop that checks the clipboard for URLs.
    """
    # pylint: disable=import-outside-toplevel
    import flet as ft

    # pylint: disable=too-many-nested-blocks

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
                        # pylint: disable=line-too-long
                        # Need to check value in thread-safe way? Flet objects are generally not thread-safe for reading?
                        # Actually value access is local property.
                        if not download_view.url_input.value:
                            logger.info("Clipboard URL detected: %s", content)
                            download_view.url_input.value = content

                            # UI updates must be scheduled on the page
                            if page:

                                def update_ui():
                                    try:
                                        page.open(
                                            ft.SnackBar(
                                                content=ft.Text(
                                                    f"URL detected: {content}"
                                                )
                                            )
                                            # pylint: disable=line-too-long
                                            # pylint: disable=broad-exception-caught
                                        )
                                        download_view.update()  # Update the view so the input field shows the value
                                    # pylint: disable=broad-exception-caught
                                    except Exception as ex:
                                        logger.warning(
                                            "Failed to update UI from clipboard: %s",
                                            ex,
                                            # pylint: disable=line-too-long
                                        )

                                # Use page.run_task or just calling page.update if thread-safe enough?
                                # Flet's page.update() is thread-safe wrapper.
                                # But modify controls might not be if they are mid-render.
                                # However, setting .value is just property setting.
                                update_ui()

            except Exception as e:  # pylint: disable=broad-exception-caught
                # Catch-all to prevent thread death
                logger.error("Error in clipboard monitor: %s", e, exc_info=True)
