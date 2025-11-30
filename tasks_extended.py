import threading
import logging
from downloader.info import get_video_info
from app_state import state

logger = logging.getLogger(__name__)


def fetch_info_task(url, download_view, page):
    """Fetch video info in background with cookie support."""
    logger.info(f"Starting metadata fetch for: {url}")
    try:
        # Get selected browser cookies if available
        cookies_from_browser = None
        if download_view and hasattr(download_view, "cookies_dd"):
            cookies_value = download_view.cookies_dd.value

            if cookies_value and cookies_value != "None":
                cookies_from_browser = cookies_value
                logger.debug(f"Using browser cookies: {cookies_from_browser}")

        info = get_video_info(url, cookies_from_browser=cookies_from_browser)
        if not info:
            raise Exception("Failed to fetch info")
        state.video_info = info
        logger.info(f"Metadata fetched successfully for: {info.get('title', 'Unknown Title')}")

        if download_view:
            download_view.update_info(info)

        # We need to be careful updating UI from background thread
        # Flet is usually thread-safe for page.update() but it's good practice to verify
        if page:
            import flet as ft

            page.open(ft.SnackBar(content=ft.Text("Metadata fetched successfully")))
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        if page:
            import flet as ft

            page.open(ft.SnackBar(content=ft.Text(f"Error: {e}")))
    finally:
        if download_view:
            download_view.fetch_btn.disabled = False
        if page:
            page.update()
