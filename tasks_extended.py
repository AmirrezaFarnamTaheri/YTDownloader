"""
Extended background tasks, specifically for fetching metadata.
"""

import logging
from typing import Optional

import flet as ft

from app_state import state
from downloader.info import get_video_info
from localization_manager import LocalizationManager as LM

logger = logging.getLogger(__name__)


def fetch_info_task(url: str, download_view, page: Optional[ft.Page]):
    """Fetch video info in background with cookie support."""
    logger.info("Starting metadata fetch for: %s", url)
    try:
        # Get selected browser cookies if available
        cookies_from_browser = None
        if download_view and hasattr(download_view, "cookies_dd"):
            cookies_value = download_view.cookies_dd.value

            if cookies_value and cookies_value != "None":
                cookies_from_browser = cookies_value
                logger.debug("Using browser cookies: %s", cookies_from_browser)

        info = get_video_info(url, cookies_from_browser=cookies_from_browser)
        if not info:
            logger.error("get_video_info returned None for %s", url)
            raise RuntimeError("Failed to fetch info")
        state.video_info = info
        try:
            state.set_video_info(url, info)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.debug("Failed to cache video info for %s", url)
        logger.info(
            "Metadata fetched successfully for: %s",
            info.get("title", "Unknown Title"),
        )
        logger.debug("Metadata keys: %s", list(info.keys()))

        def update_ui_success():
            if download_view:
                logger.debug("Updating DownloadView with new info")
                download_view.update_info(info)
                download_view.fetch_btn.disabled = False
            if page:
                page.open(
                    ft.SnackBar(content=ft.Text(LM.get("metadata_fetch_success")))
                )
                page.update()

        if page and hasattr(page, "run_task"):
            page.run_task(update_ui_success)
        else:
            update_ui_success()

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Fetch error: %s", e)

        def update_ui_error():
            if download_view:
                download_view.fetch_btn.disabled = False
                download_view.update()
            if page:
                page.open(
                    ft.SnackBar(
                        content=ft.Text(LM.get("metadata_fetch_failed", str(e)))
                    )
                )
                page.update()

        if page and hasattr(page, "run_task"):
            page.run_task(update_ui_error)
        else:
            update_ui_error()
