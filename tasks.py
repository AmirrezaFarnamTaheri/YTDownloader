import logging
import threading
import time
from datetime import datetime, timedelta

from app_state import state
from downloader import download_video
from history_manager import HistoryManager
from ui_utils import format_file_size
from utils import CancelToken

logger = logging.getLogger(__name__)

# Lock to prevent concurrent process_queue calls
_process_queue_lock = threading.RLock()  # RLock to allow recursive calls safely
_active_downloads = threading.Semaphore(3)  # Limit concurrent downloads


def process_queue():
    """
    Process the queue to start the next download.
    Uses a lock to prevent race conditions from concurrent calls.
    """
    # Non-blocking acquire to prevent pileup
    acquired = _process_queue_lock.acquire(blocking=False)
    if not acquired:
        # logger.debug("process_queue already running, skipping") # Too noisy
        return

    try:
        # logger.debug("Entered process_queue critical section")
        _process_queue_impl()
    except Exception as e:
        logger.error(f"Error in process_queue critical section: {e}", exc_info=True)
    finally:
        _process_queue_lock.release()


def _process_queue_impl():
    """Internal implementation separated from lock management."""
    # Check for scheduled items and update them atomically via QueueManager API
    now = datetime.now()
    queue_mgr = state.queue_manager
    # Prefer the dedicated API for real QueueManager instances,
    # but fall back to legacy direct access for mocked instances in tests.
    try:
        from queue_manager import QueueManager  # local import to avoid cycles
    except Exception:
        QueueManager = None  # type: ignore

    if QueueManager is not None and isinstance(queue_mgr, QueueManager):
        queue_mgr.update_scheduled_items(now)
    else:
        # Legacy path for tests
        lock = getattr(queue_mgr, "_lock", None)
        q = getattr(queue_mgr, "_queue", None)
        if lock is not None and q is not None:
            with lock:
                for item in q:
                    if item.get("scheduled_time") and str(
                        item.get("status", "")
                    ).startswith("Scheduled"):
                        # Add 1 second tolerance to avoid missing by milliseconds
                        scheduled = item["scheduled_time"]
                        if isinstance(scheduled, datetime):
                            # Allow up to 1 second early
                            if now >= (scheduled - timedelta(seconds=1)):
                                item["status"] = "Queued"
                                item["scheduled_time"] = None

    # ATOMIC CLAIM
    item = state.queue_manager.claim_next_downloadable()
    if item:
        item_title = item.get("title", item.get("url", "Unknown"))
        logger.debug(f"Claimed item for processing: {item_title}")
        # Check if we can start another download
        if _active_downloads.acquire(blocking=False):
            logger.info(
                f"Starting download task for: {item_title} "
                f"(Active: {3 - _active_downloads._value}/3)"
            )
            thread = threading.Thread(
                target=download_task,
                args=(item,),
                daemon=True,
                name=f"Download-{item_title[:20]}",
            )
            thread.start()
        else:
            logger.info(
                f"Max concurrent downloads reached, returning {item_title} to queue"
            )
            item["status"] = "Queued"  # Reset for next attempt


def download_task(item):
    item["status"] = "Downloading"
    state.current_download_item = item
    state.cancel_token = CancelToken()

    # Set thread name for debugging
    thread = threading.current_thread()
    old_name = thread.name
    item_title = item.get("title", "Unknown")
    thread.name = f"DL-{item_title[:15]}"

    logger.info(f"Thread started for download task: {item_title}")

    # Ensure we release the semaphore
    try:
        logger.debug(f"Entering download_task implementation for {item.get('url')}")
        return _download_task_impl(item)
    except Exception as e:
        logger.error(
            f"Unhandled exception in download_task wrapper: {e}", exc_info=True
        )
    finally:
        thread.name = old_name
        _active_downloads.release()
        logger.info(
            f"Download task finished. Slot released. "
            f"Available slots: {3 - (2 - _active_downloads._value)}"
        )


def _download_task_impl(item):
    """Internal download implementation."""

    if "control" in item:
        item["control"].update_progress()

    try:

        def progress_hook(d, _):
            # Throttle progress updates to reduce UI spam
            # BUT always process 'finished' or other terminal states
            is_terminal = d.get("status") in ["finished", "error"]

            if not is_terminal:
                current_time = time.time()
                last_update = item.get("_last_progress_update", 0)

                # Update at most every 0.5 seconds
                if current_time - last_update < 0.5:
                    return

                item["_last_progress_update"] = current_time

            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = downloaded / total

                    # Only update if change is significant (> 1%)
                    last_pct = item.get("_last_pct", 0)
                    if abs(pct - last_pct) < 0.01:
                        return
                    item["_last_pct"] = pct

                    if "control" in item:
                        item["control"].progress_bar.value = pct

                item["speed"] = format_file_size(d.get("speed", 0)) + "/s"
                item["size"] = format_file_size(total)
                item["eta"] = f"{d.get('eta', 0)}s"

                if "control" in item:
                    item["control"].update_progress()

            elif d["status"] == "finished":
                item["status"] = "Processing"
                if "control" in item:
                    item["control"].progress_bar.value = 1.0
                    item["control"].update_progress()
                item["final_filename"] = d.get("filename")

        # Extract cookies if passed
        cookies = item.get("cookies_from_browser")

        download_video(
            item["url"],
            progress_hook,
            item,
            video_format=item.get("video_format", "best"),
            output_path=item.get("output_path"),
            cancel_token=state.cancel_token,
            sponsorblock_remove=item.get("sponsorblock", False),
            playlist=item.get("playlist", False),
            use_aria2c=item.get("use_aria2c", False),
            gpu_accel=item.get("gpu_accel"),
            output_template=item.get("output_template"),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            force_generic=item.get("force_generic", False),
            cookies_from_browser=cookies,
        )

        logger.info(f"Download successful: {item.get('title')}")

        # Add to history first, then mark as completed
        try:
            HistoryManager.add_entry(
                url=item["url"],
                title=item.get("title", "Unknown"),
                output_path=item.get("output_path"),
                format_str=item.get("video_format"),
                status="Completed",
                file_size=item.get("size", "N/A"),
                file_path=item.get("final_filename"),
            )
        except Exception as history_error:
            logger.error(f"Failed to add entry to history: {history_error}")
            # Continue anyway - download succeeded even if history failed

        item["status"] = "Completed"

    except Exception as e:
        if "cancelled" in str(e).lower():
            logger.info(f"Download cancelled by user: {item.get('title')}")
            item["status"] = "Cancelled"
        else:
            item["status"] = "Error"
            try:
                logger.error(
                    f"Download failed for {item.get('title')}: {e}", exc_info=True
                )
            except ValueError:
                # Logging system might be closed during shutdown/tests
                pass
    finally:
        if "control" in item:
            item["control"].update_progress()
        state.current_download_item = None
        state.cancel_token = None

        # Don't call process_queue recursively - use a delayed trigger instead
        timer = threading.Timer(1.0, process_queue)
        timer.daemon = True
        timer.start()
