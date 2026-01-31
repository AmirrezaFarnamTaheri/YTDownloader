"""
Tasks module.
Handles background tasks like downloading, fetching info, etc.
Executes operations that shouldn't block the UI thread.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import flet as ft

import app_state
from downloader.core import download_video
from downloader.info import get_video_info
from downloader.types import DownloadOptions, DownloadStatus
from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from queue_manager import CancelToken
from ui_utils import get_default_download_path

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_WORKERS = 3
_SUBMISSION_THROTTLE = threading.Semaphore(
    DEFAULT_MAX_WORKERS
)  # Control task submission rate to executor
_ACTIVE_COUNT_LOCK = threading.Lock()

# Legacy aliases for tests
_executor_lock = threading.Lock()
_executor = None


def configure_concurrency(max_workers):
    """
    Reconfigures the global thread pool executor with a new max_workers limit.
    Correctly updates the submission throttle without orphaning running tasks.
    """
    global _executor, _SUBMISSION_THROTTLE

    # Update global executor reference to force new pool creation on next use
    # We don't shutdown the old one immediately if we want running tasks to finish,
    # but ThreadPoolExecutor(wait=False) is typical for "fire and forget" shutdown.
    with _executor_lock:
        if _executor:
            _executor.shutdown(wait=False)
            _executor = None

    # Update throttle semaphore
    # We create a new semaphore. Running tasks will release the OLD semaphore instance
    # if they captured it in their closure. New tasks will use the NEW semaphore.
    # This might temporarily exceed the limit if we reduce it, but it's safe.
    _SUBMISSION_THROTTLE = threading.Semaphore(max_workers)

    logger.info("Concurrency limit updated to %d", max_workers)


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
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=_get_max_workers())
        return _executor


def _log_to_history(item: dict, result: dict | None) -> None:
    """Helper to add completed/failed download to history."""
    try:
        if app_state.state.history_manager:
            entry = {
                "url": item.get("url", ""),
                "title": item.get("title", "Unknown"),
                "status": str(item.get("status", "Unknown")),
                "filename": result.get("filename") if result else "",
                "filepath": result.get("filepath") if result else "",
                "file_size": (
                    result.get("file_size") if result else item.get("file_size")
                ),
            }
            app_state.state.history_manager.add_entry(entry)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to log history: %s", e)


class DownloadJob:
    """
    Encapsulates the state and logic for a single download task.
    """

    def __init__(self, item: dict, page: ft.Page | None):
        self.item = item
        self.page = page
        self.item_id = item.get("id")
        self.qm = app_state.state.queue_manager
        self.cancel_token = CancelToken()
        self.url = item.get("url", "")

    def run(self):
        """Execute the download job."""
        if not self.url or not self.item_id:
            logger.error("Invalid job item: %s", self.item)
            return

        # Check shutdown
        flag = getattr(app_state.state, "shutdown_flag", None)
        if flag and flag.is_set():
            self.qm.update_item_status(self.item_id, DownloadStatus.CANCELLED)
            return

        self.qm.register_cancel_token(self.item_id, self.cancel_token)

        try:
            self._execute_download()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._handle_error(e)
        finally:
            self.qm.unregister_cancel_token(self.item_id, self.cancel_token)

    def _execute_download(self):
        self.qm.update_item_status(self.item_id, DownloadStatus.DOWNLOADING)

        options = self._build_options()
        logger.info("Starting download for %s", self.url)

        result = download_video(options)

        self.qm.update_item_status(self.item_id, DownloadStatus.COMPLETED, result)
        _log_to_history(self.item, result)

        if self.page:
            self._notify_success()

    def _build_options(self) -> DownloadOptions:
        preferred_path = app_state.state.config.get("download_path")
        output_path = self.item.get("output_path") or get_default_download_path(preferred_path)

        # Ensure item has the resolved path
        if not self.item.get("output_path"):
            self.item["output_path"] = output_path

        # Resolve Proxy/Rate Limit/Cookies from item or global config
        proxy = self.item.get("proxy") or app_state.state.config.get("proxy")
        rate_limit = self.item.get("rate_limit") or app_state.state.config.get("rate_limit")
        cookies = self.item.get("cookies_from_browser") or app_state.state.config.get("cookies")

        # Clean empty strings
        proxy = proxy if isinstance(proxy, str) and proxy else None
        rate_limit = rate_limit if isinstance(rate_limit, str) and rate_limit else None

        video_fmt = self.item.get("video_format", "best")
        if self.item.get("audio_only", False):
            video_fmt = "audio"

        tpl = app_state.state.config.get("output_template")

        return DownloadOptions(
            url=self.url,
            output_path=output_path,
            progress_hook=self._progress_hook,
            playlist=self.item.get("playlist", False),
            proxy=proxy,
            rate_limit=rate_limit,
            cookies_from_browser=cookies,
            cancel_token=self.cancel_token,
            video_format=video_fmt,
            audio_format=self.item.get("audio_format"),
            start_time=self.item.get("start_time"),
            end_time=self.item.get("end_time"),
            force_generic=self.item.get("force_generic", False),
            output_template=tpl if tpl else "%(title)s.%(ext)s",
            sponsorblock=self.item.get("sponsorblock", False),
            use_aria2c=self.item.get("use_aria2c", False),
            gpu_accel=self.item.get("gpu_accel"),
        )

    def _progress_hook(self, d):
        if self.cancel_token:
            self.cancel_token.check()

        if d["status"] == "downloading":
            try:
                p = d.get("_percent_str", "0%").replace("%", "")
                progress_val = float(p) / 100

                # Update item directly in shared dict is not safe?
                # QueueManager updates are atomic.
                # Just send update to QM.
                updates = {
                    "progress": progress_val,
                    "speed": d.get("_speed_str", ""),
                    "eta": d.get("_eta_str", ""),
                    "size": d.get("_total_bytes_str", "")
                }

                self.qm.update_item_status(
                    self.item_id, DownloadStatus.DOWNLOADING, updates
                )
            except Exception as e:
                logger.debug("Error in progress hook: %s", e)

        elif d["status"] == "finished":
            self.qm.update_item_status(self.item_id, DownloadStatus.PROCESSING, {"progress": 1.0})

    def _handle_error(self, e: Exception):
        err_str = str(e)
        if "Cancelled" in err_str or (self.cancel_token and self.cancel_token.cancelled):
            logger.info("Download cancelled for %s", self.url)
            self.qm.update_item_status(self.item_id, DownloadStatus.CANCELLED)
            _log_to_history(self.item, None)
        else:
            logger.error("Download failed for %s: %s", self.url, e)
            self.qm.update_item_status(self.item_id, DownloadStatus.ERROR, {"error": str(e)})
            _log_to_history(self.item, None)
            if self.page:
                self._notify_error()

    def _notify_success(self):
        async def show():
            self.page.open(
                ft.SnackBar(
                    content=ft.Text(f"{LM.get('download_complete')}: {self.item.get('title')}")
                )
            )
        self.page.run_task(show)

    def _notify_error(self):
        async def show():
            self.page.open(
                ft.SnackBar(
                    content=ft.Text(f"{LM.get('download_error')} (Check logs)"),
                    bgcolor=ft.colors.ERROR
                )
            )
        self.page.run_task(show)


def process_queue(page: ft.Page | None) -> None:
    """
    Main loop to process queue items.
    """
    flag = getattr(app_state.state, "shutdown_flag", None)
    if flag and flag.is_set():
        return

    qm = app_state.state.queue_manager
    if not qm:
        return

    # Check active count
    active_count = qm.get_active_count()
    max_workers = _get_max_workers()

    if active_count >= max_workers:
        return

    # Attempt to acquire semaphore non-blocking
    if not _SUBMISSION_THROTTLE.acquire(blocking=False):
        return

    item = None
    submitted = False

    # Capture the semaphore used for acquisition to release it correctly
    # even if global changes later (though configure_concurrency logic tries to handle it).
    throttle_ref = _SUBMISSION_THROTTLE

    try:
        item = qm.claim_next_downloadable()
        if not item:
            return

        logger.info("Submitting job for %s (ID: %s)", item.get("url"), item.get("id"))

        executor = _get_executor()

        def _job_wrapper(it: dict, pg: ft.Page | None, sem: threading.Semaphore):
            try:
                job = DownloadJob(it, pg)
                job.run()
            finally:
                sem.release()

        executor.submit(_job_wrapper, item, page, throttle_ref)
        submitted = True

    except Exception:
        if item and "id" in item:
            qm.update_item_status(item["id"], DownloadStatus.QUEUED)
        raise
    finally:
        if not submitted:
            throttle_ref.release()


# Legacy wrapper if needed (for tests relying on download_task function directly)
def download_task(item: dict, page: ft.Page | None) -> None:
    """Legacy wrapper for DownloadJob."""
    job = DownloadJob(item, page)
    job.run()


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
                if hasattr(view_card, "set_fetch_disabled"):
                    view_card.set_fetch_disabled(False)
                page.open(
                    ft.SnackBar(
                        content=ft.Text(f"{LM.get('error_fetch_info')}: {str(e)}")
                    )
                )

            page.run_task(show_error)
