import threading
import time
import logging
import pyperclip
from ui_utils import validate_url
from app_state import state

logger = logging.getLogger(__name__)


def start_clipboard_monitor(page, download_view):
    """Starts the clipboard monitor thread."""
    threading.Thread(
        target=_clipboard_loop, args=(page, download_view), daemon=True
    ).start()


def _clipboard_loop(page, download_view):
    """
    Background loop that checks the clipboard for URLs.
    """
    while True:
        # Check if main thread is alive, if not, stop (rudimentary check)
        if not threading.main_thread().is_alive():
            break

        time.sleep(2)
        if state.clipboard_monitor_active:
            try:
                # pyperclip.paste() might fail in headless envs without xclip/xsel
                try:
                    content = pyperclip.paste()
                except pyperclip.PyperclipException:
                    # If clipboard is unavailable, just ignore and continue
                    continue

                if content and content != state.last_clipboard_content:
                    state.last_clipboard_content = content
                    if validate_url(content) and download_view:
                        # Only auto-paste if field is empty
                        if not download_view.url_input.value:
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
