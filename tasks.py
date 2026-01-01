"""
Tasks module.
Handles background tasks like downloading, fetching info, etc.
Executes operations that shouldn't block the UI thread.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import flet as ft

import app_state
from downloader.core import download_video
from downloader.info import get_video_info
from downloader.types import DownloadOptions
from downloader.utils.constants import RESERVED_FILENAMES
from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from queue_manager import CancelToken
from ui_utils import get_default_download_path

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_WORKERS = 3
_SUBMISSION_THROTTLE = threading.Semaphore(
    1
)  # Control task submission rate to executor
_ACTIVE_COUNT_LOCK = threading.Lock()


def _get_max_workers() -> int:
    try:
        val = int(
            app_state.state.config.get("max_concurrent_downloads", DEFAULT_MAX_WORKERS)
        )
        return val if val > 0 else DEFAULT_MAX_WORKERS
    except Exception:  # pylint: disable=broad-exception-caught
        return DEFAULT_MAX_WORKERS


def _get_executor() -> ThreadPoolExecutor:
    """Lazy initializer for executor to pick up config changes."""
    # Note: We are not caching executor here to allow resizing if config changes?
    # Actually, resizing ThreadPoolExecutor is not trivial.
    # For simplicity, we use a global executor but we might want to recreate it if config changes.
    # For now, let's assume a fixed pool or we just use a new one if we really wanted dynamic sizing.
    # BUT, creating new executors for every task is bad.
    # We'll use a module-level cached executor that we initialized at app start or on first use.
    if not hasattr(_get_executor, "executor") or _get_executor.executor is None:
        _get_executor.executor = ThreadPoolExecutor(max_workers=_get_max_workers())
    return _get_executor.executor


def _log_to_history(item: dict, result: dict | None) -> None:
    """Helper to add completed/failed download to history."""
    try:
        if app_state.state.history_manager:
            entry = {
                "url": item.get("url", ""),
                "title": item.get("title", "Unknown"),
                "status": item.get("status", "Unknown"),
                "filename": result.get("filename") if result else "",
                "filepath": result.get("filepath") if result else "",
                "file_size": (
                    result.get("file_size") if result else item.get("file_size")
                ),
            }
            app_state.state.history_manager.add_entry(entry)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to log history: %s", e)


def _progress_hook_factory(item: dict, cancel_token: CancelToken):
    """Creates a progress hook for yt-dlp/downloader."""

    def progress_hook(d):
        if cancel_token and cancel_token.is_cancelled():
            raise Exception("Download Cancelled by user")

        if d["status"] == "downloading":
            try:
                p = d.get("_percent_str", "0%").replace("%", "")
                progress_val = float(p) / 100
                item["progress"] = progress_val
                item["status"] = "Downloading"
                # We could update UI here, but better to let the polling loop handle it
                # or call queue_manager to notify listeners.
                # app_state.state.queue_manager.update_item_progress(item['id'], progress_val)
                # For high frequency updates, we write to item dict (shared state)
                # and let the UI polling loop (if any) or QueueView rebuild pick it up.
                # BUT, QueueManager handles thread safety for the item dict?
                # Actually QueueManager returns COPIES. So modifying 'item' here locally won't affect QueueManager state
                # unless 'item' is the reference from inside QueueManager (which it is not, usually).
                # We MUST call queue_manager.update_item_progress.
                if "id" in item:
                    app_state.state.queue_manager.update_item_progress(
                        item["id"], progress_val
                    )

            except Exception:  # pylint: disable=broad-exception-caught
                pass
        elif d["status"] == "finished":
            item["progress"] = 1.0
            item["status"] = "Processing"
            if "id" in item:
                app_state.state.queue_manager.update_item_status(
                    item["id"], "Processing"
                )

    return progress_hook


def process_queue(page: ft.Page | None) -> None:
    """
    Main loop to process queue items.
    Should be called periodically or triggered by events.
    Running in background thread usually.
    """
    # Quick check for shutdown
    if getattr(app_state.state, "shutdown_flag", False):
        return

    qm = app_state.state.queue_manager
    if not qm:
        return

    # 1. Check active downloads count
    # We can get active count from QM
    active_count = qm.get_active_count()
    max_workers = _get_max_workers()

    if active_count >= max_workers:
        return  # Busy

    # 2. Claim next item
    item = qm.claim_next_downloadable()
    if not item:
        return

    logger.info("Starting download for %s", item.get("url"))

    # 3. Submit to executor
    executor = _get_executor()
    # We use a throttle to ensure we don't spam executor if it's somehow backed up
    # preserving order is handled by QueueManager priority/order.
    if _SUBMISSION_THROTTLE.acquire(blocking=False):
        try:
            executor.submit(download_task, item, page)
        except RuntimeError:
            # Executor might be closed
            logger.error("Executor is closed, cannot submit task.")
            # Release item back to queue? Or fail it?
            # Reverting status to Queued
            qm.update_item_status(item["id"], "Queued")
        finally:
            _SUBMISSION_THROTTLE.release()
    else:
        # Throttle busy, revert item claim?
        # Ideally we shouldn't have claimed it if we couldn't submit.
        # But claim sets status to "Allocating" or similar?
        # If claim_next_downloadable sets status to "Downloading", we must revert if submission fails.
        # Assuming claim sets it to "Allocating" or "Downloading".
        # Let's revert.
        qm.update_item_status(item["id"], "Queued")


def download_task(item: dict, page: ft.Page | None) -> None:
    """
    The actual download work.
    """
    url = item.get("url")
    if not url:
        return

    # Check shutdown again
    if getattr(app_state.state, "shutdown_flag", False):
        if "id" in item:
            app_state.state.queue_manager.update_item_status(item["id"], "Cancelled")
        return

    item_id = item.get("id")
    qm = app_state.state.queue_manager

    # Create CancelToken
    cancel_token = CancelToken()
    if item_id:
        qm.register_cancel_token(item_id, cancel_token)

    try:
        # Update status
        qm.update_item_status(item_id, "Downloading")

        # Prepare hooks and execute
        phook = _progress_hook_factory(item, cancel_token)

        preferred_path = None
        if hasattr(app_state.state, "config") and hasattr(
            app_state.state.config, "get"
        ):
            preferred_path = app_state.state.config.get("download_path")
        output_path = item.get("output_path") or get_default_download_path(
            preferred_path
        )
        if not item.get("output_path"):
            item["output_path"] = output_path
        logger.debug("Resolved output path for %s: %s", url, output_path)

        proxy = item.get("proxy")
        if (
            not proxy
            and hasattr(app_state.state, "config")
            and hasattr(app_state.state.config, "get")
        ):
            cfg_proxy = app_state.state.config.get("proxy")
            proxy = cfg_proxy if isinstance(cfg_proxy, str) and cfg_proxy else None
        if proxy:
            logger.debug("Proxy enabled for %s", url)

        rate_limit = item.get("rate_limit")
        if (
            not rate_limit
            and hasattr(app_state.state, "config")
            and hasattr(app_state.state.config, "get")
        ):
            cfg_rate = app_state.state.config.get("rate_limit")
            rate_limit = cfg_rate if isinstance(cfg_rate, str) and cfg_rate else None
        if rate_limit:
            logger.debug("Rate limit set for %s: %s", url, rate_limit)

        cookies = item.get("cookies_from_browser")
        if not cookies:
            # Check global config for cookies default?
            # Usually cookies are per-download or global.
            # ConfigManager handles "cookies" key which is the browser name (e.g. "chrome")
            # But here we expect the item to carry it if overridden, or we check config.
            if hasattr(app_state.state, "config") and hasattr(
                app_state.state.config, "get"
            ):
                cookies = app_state.state.config.get("cookies")

        # Check for force_generic
        force_generic = item.get("force_generic", False)

        options = DownloadOptions(
            url=url,
            output_path=output_path,
            progress_hook=phook,
            noplaylist=not item.get("playlist", False),
            proxy=proxy,
            rate_limit=rate_limit,
            cookies_from_browser=cookies,
            cancel_token=cancel_token,
            format_id=item.get("format_id"),
            audio_only=item.get("audio_only", False),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            force_generic=force_generic,
        )

        # If output_template is in config, we might want to pass it?
        # But download_video uses default if not provided.
        # We should check config for output_template
        if hasattr(app_state.state, "config") and hasattr(
            app_state.state.config, "get"
        ):
            tpl = app_state.state.config.get("output_template")
            if tpl:
                options.output_template = tpl

        logger.info("Calling download_video for %s", url)
        result = download_video(options)

        # Success
        qm.update_item_status(item_id, "Completed", result)
        _log_to_history(item, result)

        if page:
            page.open(
                ft.SnackBar(
                    content=ft.Text(
                        f"{LM.get('download_complete')}: {item.get('title')}"
                    )
                )
            )

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Check if cancelled
        err_str = str(e)
        if "Cancelled" in err_str or (cancel_token and cancel_token.is_cancelled()):
            logger.info("Download cancelled for %s", url)
            qm.update_item_status(item_id, "Cancelled")
            _log_to_history(item, None)  # Should we log cancelled? Maybe.
        else:
            logger.error("Download failed for %s: %s", url, e)
            qm.update_item_status(item_id, "Error")
            # Update item error msg?
            # QueueManager items are dicts, we can add error field?
            # Not standardized, but useful.
            _log_to_history(item, None)
            if page:
                page.open(
                    ft.SnackBar(
                        content=ft.Text(f"{LM.get('download_error')}: {err_str}"),
                        bgcolor=ft.colors.ERROR,
                    )
                )
    finally:
        if item_id:
            qm.unregister_cancel_token(item_id, cancel_token)


def fetch_info_task(url: str, view_card: Any, page: Any) -> None:
    """
    Fetches video info in background and updates UI.
    """
    # Disable fetch UI control
    if hasattr(view_card, "set_fetch_disabled"):
        view_card.set_fetch_disabled(True)
    try:
        # Check cookies
        cookies = None
        if hasattr(view_card, "cookies_dd") and view_card.cookies_dd.value != "None":
            cookies = view_card.cookies_dd.value

        info = get_video_info(url, cookies_from_browser=cookies)

        if not info:
            raise ValueError("No video info returned")

        # Update global state
        app_state.state.video_info = info

        # Update UI safely
        if page:

            async def update_ui():
                view_card.update_video_info(info)
                # Re-enable fetch button
                view_card.set_fetch_disabled(False)
                page.open(ft.SnackBar(content=ft.Text(LM.get("info_fetched_success"))))

            page.run_task(update_ui)

    except Exception as e:
        logger.error("Fetch info failed: %s", e, exc_info=True)
        if page:

            async def show_error():
                view_card.set_fetch_disabled(False)
                page.open(
                    ft.SnackBar(
                        content=ft.Text(f"{LM.get('error_fetch_info')}: {str(e)}")
                    )
                )

            page.run_task(show_error)
