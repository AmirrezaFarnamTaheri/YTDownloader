"""
Queue Manager module for handling download tasks.
Refactored for robustness, event-driven architecture, and better cancellation support.
"""

import logging
import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, cast

from downloader.types import DownloadStatus, QueueItem
from utils import CancelToken

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Thread-safe manager for the download queue.

    # pylint: disable=too-many-public-methods

    Status Lifecycle:
    - "Queued" -> "Allocating" -> "Downloading" -> "Processing" -> "Completed"
    - "Queued" -> "Allocating" -> "Downloading" -> "Error"
    - "Queued" -> "Allocating" -> "Downloading" -> "Cancelled"
    - "Scheduled (HH:MM)" -> "Queued" (when time reached)
    """

    MAX_QUEUE_SIZE = 1000

    def __init__(self) -> None:
        # We explicitly type self._queue as list[QueueItem]
        self._queue: list[QueueItem] = []
        # Re-entrant lock for queue operations
        self._lock = threading.RLock()

        # Condition variable for background workers to wait on
        self._has_work = threading.Condition(self._lock)

        # Listeners for UI updates
        self._listeners: list[Callable[[], None]] = []
        self._listeners_lock = threading.Lock()

        # Map item IDs to their active CancelTokens
        self._cancel_tokens: dict[str, CancelToken] = {}

    @property
    def has_work_condition(self) -> threading.Condition:
        """Expose condition variable for workers."""
        return self._has_work

    def get_all(self) -> list[QueueItem]:
        """Get a copy of the current queue."""
        with self._lock:
            # Return shallow copy
            return list(self._queue)

    def get_item_by_id(self, item_id: str) -> QueueItem | None:
        """Get item by its unique ID."""
        with self._lock:
            for item in self._queue:
                if item.get("id") == item_id:
                    return cast(QueueItem, item.copy())
        return None

    def get_item_by_index(self, index: int) -> QueueItem | None:
        """Get item by its index in the queue."""
        with self._lock:
            if 0 <= index < len(self._queue):
                return cast(QueueItem, self._queue[index].copy())
        return None

    def any_downloading(self) -> bool:
        """Check if any items are currently in a downloading or active state."""
        return self.any_in_status(["Downloading", "Allocating", "Processing"])

    def any_in_status(self, status: str | list[str]) -> bool:
        """Check if any items match the given status(es)."""
        if isinstance(status, str):
            statuses = {status}
        else:
            statuses = set(status)

        with self._lock:
            for item in self._queue:
                if item.get("status") in statuses:
                    return True
        return False

    def get_active_count(self) -> int:
        """Get the number of currently active downloads."""
        with self._lock:
            return sum(
                1
                for item in self._queue
                if item.get("status") in ("Downloading", "Allocating", "Processing")
            )

    def get_queue_count(self) -> int:
        """Get the total number of items in the queue."""
        with self._lock:
            return len(self._queue)

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Add a listener callback for queue changes."""
        with self._listeners_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        """Remove a listener callback."""
        with self._listeners_lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _notify_listeners_safe(self) -> None:
        """Notify listeners safely without holding the queue lock."""
        # Snapshot listeners
        with self._listeners_lock:
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error in queue listener: %s", e)

    def add_item(self, item: dict[str, Any]) -> None:
        """Add an item to the queue."""
        if not isinstance(item, dict):
            raise ValueError("Item must be a dictionary")

        with self._lock:
            if len(self._queue) >= self.MAX_QUEUE_SIZE:
                raise ValueError("Queue is full")

            # Validate and cast to QueueItem
            # Ensure ID
            if "id" not in item:
                item["id"] = str(uuid.uuid4())

            # Ensure status
            if "status" not in item:
                item["status"] = "Queued"

            queue_item = cast(QueueItem, item)

            logger.info(
                "Adding item to queue: %s (ID: %s)",
                queue_item.get("title", queue_item.get("url")),
                queue_item["id"],
            )
            self._queue.append(queue_item)

            # Notify workers that work might be available
            # Must acquire the condition lock (which is self._lock)
            self._has_work.notify_all()

        self._notify_listeners_safe()

    def update_item_status(
        self, item_id: str, status: str, updates: dict[str, Any] | None = None
    ) -> None:
        """
        Atomically update an item's status and other fields.
        """
        updated = False
        with self._lock:
            for item in self._queue:
                if item.get("id") == item_id:
                    logger.debug(
                        "Updating status for item %s: %s -> %s",
                        item_id,
                        item.get("status"),
                        status,
                    )
                    # We assume status is a valid Literal
                    item["status"] = cast(Any, status)
                    if updates:
                        item.update(updates)
                    updated = True
                    break

            if updated and status == "Queued":
                self._has_work.notify_all()

        if updated:
            self._notify_listeners_safe()

    def remove_item(self, item: dict[str, Any]) -> None:
        """
        Remove an item from the queue and cancel it if running.
        Atomic operation.
        """
        item_id = item.get("id")
        removed = False

        with self._lock:
            # Find actual item object in queue (in case 'item' is a copy)
            target = None
            if item_id:
                for q_item in self._queue:
                    if q_item.get("id") == item_id:
                        target = q_item
                        break
            else:
                # Fallback for legacy items without IDs (shouldn't happen with strict types)
                for q_item in self._queue:
                    if q_item == item:
                        target = q_item
                        break

            if target:
                if item_id:
                    logger.info("Removing item from queue: %s", item_id)
                    # Cancel if running
                    token = self._cancel_tokens.get(item_id)
                    if token:
                        token.cancel()

                self._queue.remove(target)
                removed = True

        # Notify outside lock to prevent deadlock if listener calls back into queue
        if removed:
            self._notify_listeners_safe()

    def swap_items(self, index1: int, index2: int) -> None:
        """Swap two items in the queue."""
        changed = False
        with self._lock:
            if 0 <= index1 < len(self._queue) and 0 <= index2 < len(self._queue):
                self._queue[index1], self._queue[index2] = (
                    self._queue[index2],
                    self._queue[index1],
                )
                changed = True

        if changed:
            self._notify_listeners_safe()

    def update_scheduled_items(self, now: datetime) -> int:
        """Transition scheduled items to Queued if time reached."""
        updated = 0
        with self._lock:
            for item in self._queue:
                status = item.get("status")
                scheduled_time = item.get("scheduled_time")
                # Check for Enum or legacy string starting with Scheduled
                is_scheduled = status == DownloadStatus.SCHEDULED or str(
                    status
                ).startswith("Scheduled")
                if is_scheduled and scheduled_time:
                    if now >= scheduled_time:
                        item["status"] = "Queued"
                        item["scheduled_time"] = None
                        updated += 1

            if updated > 0:
                self._has_work.notify_all()

        if updated:
            self._notify_listeners_safe()
        return updated

    def claim_next_downloadable(self) -> QueueItem | None:
        """
        Atomically claim the next 'Queued' item.
        Also cleans up stale 'Allocating' items.
        """
        with self._lock:
            now = datetime.now()
            # Cleanup stale items (older than 60s)
            stale_threshold = timedelta(seconds=60)
            for item in self._queue:
                if item["status"] == "Allocating":
                    allocated_at = item.get("_allocated_at")
                    if allocated_at and (now - allocated_at > stale_threshold):
                        logger.warning("Resetting stale item: %s", item.get("title"))
                        item["status"] = "Queued"
                        if "_allocated_at" in item:
                            del item["_allocated_at"]

            # Find next
            for item in self._queue:
                if item["status"] == "Queued":
                    item["status"] = "Allocating"
                    item["_allocated_at"] = now
                    return item
        return None

    def wait_for_items(self, timeout: float = 2.0) -> bool:
        """
        Wait until an item is added or status changes to Queued.
        Returns True if notified, False if timed out.
        """
        # _has_work uses _lock, so we are essentially doing "with _lock: wait()"
        with self._has_work:
            return self._has_work.wait(timeout)

    def notify_workers(self) -> None:
        """Notify workers that state has changed."""
        with self._has_work:
            self._has_work.notify_all()

    # --- Cancellation Handling ---

    def register_cancel_token(self, item_id: str, token: CancelToken) -> None:
        """Register a cancel token for a running download."""
        with self._lock:
            self._cancel_tokens[item_id] = token

    def unregister_cancel_token(
        self, item_id: str, token: CancelToken | None = None
    ) -> None:
        """
        Unregister a cancel token (e.g. when finished).
        If token is provided, only remove if it matches (prevent race).
        """
        with self._lock:
            current = self._cancel_tokens.get(item_id)
            if current:
                if token is None or current is token:
                    del self._cancel_tokens[item_id]

    def cancel_item(self, item_id: str) -> None:
        """Request cancellation of a specific item."""
        with self._lock:
            token = self._cancel_tokens.get(item_id)
            if token:
                logger.info("Cancelling item ID: %s", item_id)
                token.cancel()

            # Update status only if in non-terminal state
            for item in self._queue:
                if item.get("id") == item_id:
                    # Prevent overwriting terminal statuses like
                    # 'Completed', 'Error', 'Cancelled'
                    # If it's already 'Cancelled', no harm done.
                    # 'Allocating', 'Downloading', 'Processing', 'Queued' are cancellable.
                    if item.get("status") in [
                        "Queued",
                        "Allocating",
                        "Downloading",
                        "Processing",
                    ]:
                        logger.info(
                            "Setting status to Cancelled for item ID: %s", item_id
                        )
                        item["status"] = "Cancelled"
                    break

        self._notify_listeners_safe()

    def retry_item(self, item_id: str | None) -> bool:
        """Retry a cancelled or failed item by resetting its status and progress."""
        if not item_id:
            return False

        updated = False
        with self._lock:
            for item in self._queue:
                if item.get("id") != item_id:
                    continue

                if item.get("status") not in ("Error", "Cancelled"):
                    logger.debug(
                        "Retry ignored for item %s with status %s",
                        item_id,
                        item.get("status"),
                    )
                    return False

                item.update(
                    {
                        "status": "Queued",
                        "scheduled_time": None,
                        "progress": 0,
                        "speed": "",
                        "eta": "",
                        "size": "",
                        "error": None,
                    }
                )
                updated = True
                break

            if updated:
                logger.info("Retrying item ID: %s", item_id)
                self._has_work.notify_all()

        if updated:
            self._notify_listeners_safe()
        return updated

    def cancel_all(self) -> int:
        """Cancel all active downloads in the queue."""
        cancelled_count = 0
        with self._lock:
            for item in self._queue:
                item_id = item.get("id")
                status = item.get("status", "")
                if not item_id:
                    continue

                # Only cancel active items
                if status in ("Queued", "Allocating", "Downloading", "Processing"):
                    # Cancel the token if exists
                    token = self._cancel_tokens.get(item_id)
                    if token:
                        token.cancel()

                    item["status"] = "Cancelled"
                    cancelled_count += 1

                # Also cancel scheduled items
                elif status == DownloadStatus.SCHEDULED or str(status).startswith(
                    "Scheduled"
                ):
                    item["status"] = "Cancelled"
                    item["scheduled_time"] = None
                    cancelled_count += 1

        if cancelled_count > 0:
            logger.info("Cancelled %d downloads", cancelled_count)
            self._notify_listeners_safe()

        return cancelled_count

    def pause_all(self) -> int:
        """Pause all queued downloads (prevents new downloads from starting)."""
        paused_count = 0
        with self._lock:
            for item in self._queue:
                if item.get("status") == "Queued":
                    item["status"] = "Paused"
                    item["_was_queued"] = True
                    paused_count += 1

        if paused_count > 0:
            logger.info("Paused %d queued downloads", paused_count)
            self._notify_listeners_safe()

        return paused_count

    def resume_all(self) -> int:
        """Resume all paused downloads."""
        resumed_count = 0
        with self._lock:
            for item in self._queue:
                if item.get("status") == "Paused":
                    item["status"] = "Queued"
                    item.pop("_was_queued", None)
                    resumed_count += 1

            if resumed_count > 0:
                self._has_work.notify_all()

        if resumed_count > 0:
            logger.info("Resumed %d downloads", resumed_count)
            self._notify_listeners_safe()

        return resumed_count

    def get_statistics(self) -> dict[str, int]:
        """Get queue statistics."""
        with self._lock:
            stats = {
                "total": len(self._queue),
                "queued": 0,
                "downloading": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "paused": 0,
                "scheduled": 0,
            }

            for item in self._queue:
                status = item.get("status", "")
                if status == "Queued":
                    stats["queued"] += 1
                elif status == "Downloading":
                    stats["downloading"] += 1
                elif status in ("Processing", "Allocating"):
                    stats["processing"] += 1
                elif status == "Completed":
                    stats["completed"] += 1
                elif status == "Error":
                    stats["failed"] += 1
                elif status == "Cancelled":
                    stats["cancelled"] += 1
                elif status == "Paused":
                    stats["paused"] += 1
                elif status == DownloadStatus.SCHEDULED or str(status).startswith(
                    "Scheduled"
                ):
                    stats["scheduled"] += 1

            return stats

    def clear_completed(self) -> int:
        """Remove all completed, errored, and cancelled items."""
        removed_count = 0
        with self._lock:
            items_to_remove = [
                item
                for item in self._queue
                if item.get("status") in ("Completed", "Error", "Cancelled")
            ]
            for item in items_to_remove:
                self._queue.remove(item)
                removed_count += 1

        if removed_count > 0:
            logger.info("Cleared %d completed/failed items", removed_count)
            self._notify_listeners_safe()

        return removed_count
