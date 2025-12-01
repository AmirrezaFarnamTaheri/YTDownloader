"""
Background task processing module.

Handles the download queue, threading, and status updates.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from app_state import state
from downloader.core import download_video

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent downloads
MAX_CONCURRENT_DOWNLOADS = 3
_active_downloads = threading.Semaphore(MAX_CONCURRENT_DOWNLOADS)
_thread_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS)


def process_queue():
    """
    Process items in the queue.
    Starts new downloads if slots are available.
    """
    # Check shutdown flag immediately
    if state.shutdown_flag.is_set():
        logger.debug("Shutdown flag set, skipping process_queue")
        return

    # Log semaphore state for debugging (try-except for shutdown race conditions)
    try:
        # pylint: disable=protected-access
        logger.debug(
            "Processing queue. Active slots: %d/%d",
            MAX_CONCURRENT_DOWNLOADS - _active_downloads._value,
            MAX_CONCURRENT_DOWNLOADS,
        )
    except ValueError:
        pass

    while True:
        if state.shutdown_flag.is_set():
            break

        # Check if we have slots available
        if not _active_downloads.acquire(blocking=False):
            # No slots available
            break

        # Get next item
        item = state.queue_manager.claim_next_downloadable()
        if not item:
            _active_downloads.release()
            break

        # Start download in a thread
        try:
            # We use a daemon thread so it doesn't block exit,
            # but ideally we should handle cancellation.
            t = threading.Thread(
                target=download_task, args=(item,), daemon=True, name=f"DL-{item['url']}"
            )
            t.start()
        except Exception as e:
            logger.error("Failed to start download thread: %s", e)
            item["status"] = "Error"
            _active_downloads.release()


def download_task(item):
    """
    Worker function for a single download.
    """
    url = item["url"]
    logger.info("Starting download task for: %s", url)

    # Set as current item for cancellation mapping
    # (Simple approach: global current_download_item is just one of them.
    # For multiple concurrent, we rely on the item['control'] or token passed.)
    # state.current_download_item = item  <-- This global is problematic for concurrency
    # We will pass a cancel token specific to this download if possible,
    # or rely on the downloader logic to handle it.
    # The current Architecture seems to support cancellation via CancelToken in state.
    # To support multiple, we would need a token per item.
    # For now, we reuse the shared state structure but be aware of limitations.

    try:
        # Update status
        item["status"] = "Downloading"
        if "control" in item:
            item["control"].update_progress()

        def progress_hook(d):
            if state.shutdown_flag.is_set():
                raise Exception("Shutdown initiated")

            if d["status"] == "downloading":
                p = d.get("_percent_str", "0%").replace("%", "")
                try:
                    progress = float(p) / 100
                except ValueError:
                    progress = 0
                item["progress"] = progress
                item["speed"] = d.get("_speed_str", "N/A")
                item["eta"] = d.get("_eta_str", "N/A")
                item["size"] = d.get("_total_bytes_str", "N/A")
                if "control" in item:
                    item["control"].update_progress()

            elif d["status"] == "finished":
                item["progress"] = 1.0
                item["status"] = "Processing"
                if "control" in item:
                    item["control"].update_progress()

        # Execute download
        info = download_video(
            url=url,
            output_path=item.get("output_path", "."),
            video_format=item.get("video_format", "best"),
            progress_hook=progress_hook,
            cancel_token=None,  # Pass specific token if implemented
            playlist=item.get("playlist", False),
            sponsorblock=item.get("sponsorblock", False),
            use_aria2c=item.get("use_aria2c", False),
            gpu_accel=item.get("gpu_accel"),
            output_template=item.get("output_template", "%(title)s.%(ext)s"),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            force_generic=item.get("force_generic", False),
            cookies_from_browser=item.get("cookies_from_browser"),
        )

        item["status"] = "Completed"
        item["filename"] = info.get("filename", "Unknown")
        item["progress"] = 1.0

        # Add to history
        try:
            from history_manager import HistoryManager

            HistoryManager.add_entry(
                url,
                item.get("title", url),
                item.get("output_path", "."),
                item.get("video_format", "best"),
                "Completed",
                item.get("size", "Unknown"),
                info.get("filepath"),  # Use actual file path if available
            )
        except Exception as e:
            logger.error("Failed to add to history: %s", e)

        # Notify UI
        if "control" in item:
            item["control"].update_progress()

        # Notify Desktop
        # if not state.shutdown_flag.is_set():
        #     from ui_utils import show_notification
        #     show_notification("Download Complete", f"{item.get('title', url)}")

    except Exception as e:
        if "Cancelled" in str(e) or item.get("status") == "Cancelled":
            logger.info("Download cancelled: %s", url)
            item["status"] = "Cancelled"
        else:
            logger.error("Download failed: %s", e, exc_info=True)
            item["status"] = "Error"
            item["error"] = str(e)

        if "control" in item:
            item["control"].update_progress()

    finally:
        # Release semaphore
        _active_downloads.release()
        try:
            # pylint: disable=protected-access
            # Corrected log message
            active_count = MAX_CONCURRENT_DOWNLOADS - _active_downloads._value
            logger.info("Download task finished. Slots used: %d/%d",
                       active_count, MAX_CONCURRENT_DOWNLOADS)
        except ValueError:
            pass

        # Trigger queue check for next items
        process_queue()
