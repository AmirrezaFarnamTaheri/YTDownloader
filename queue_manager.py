import threading
from typing import List, Dict, Any, Optional, Callable
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Thread-safe manager for the download queue.

    Status Lifecycle:
    - "Queued" -> "Allocating" -> "Downloading" -> "Processing" -> "Completed"
    - "Queued" -> "Allocating" -> "Downloading" -> "Error"
    - "Queued" -> "Allocating" -> "Downloading" -> "Cancelled"
    - "Scheduled (HH:MM)" -> "Queued" (when time reached)

    Status Descriptions:
    - Queued: Waiting to be downloaded
    - Scheduled (HH:MM): Scheduled for later execution
    - Allocating: Claimed by a worker (transitional state)
    - Downloading: Currently downloading
    - Processing: Post-processing (FFmpeg, SponsorBlock, etc.)
    - Completed: Successfully finished
    - Cancelled: User cancelled
    - Error: Failed with error
    """

    # Maximum queue size to prevent memory exhaustion
    MAX_QUEUE_SIZE = 1000

    def __init__(self):
        self._queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._listeners: List[Callable[[], None]] = []

    def get_all(self) -> List[Dict[str, Any]]:
        """Get a copy of the current queue."""
        with self._lock:
            return list(self._queue)

    def get_item_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get item by index safely."""
        with self._lock:
            if 0 <= index < len(self._queue):
                return self._queue[index]
        return None

    def add_listener(self, listener: Callable[[], None]):
        """Add a listener callback for queue changes."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]):
        """Remove a listener callback."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _notify_listeners_safe(self):
        """
        Helper to notify listeners.
        It safely copies the listener list under lock (if needed) or relies on the fact
        that we are calling it outside the lock but need to be careful about concurrency.

        Current strategy:
        1. Acquire lock briefly to copy listeners.
        2. Iterate over copy and call them.
        """
        listeners = []
        with self._lock:
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener()
            except Exception as e:
                logger.debug(f"Error in queue listener (non-critical): {e}")
                # Don't propagate listener errors

    def add_item(self, item: Dict[str, Any]):
        """
        Add an item to the queue.

        Raises:
            ValueError: If queue is at maximum capacity.
        """
        if not item or not isinstance(item, dict):
            raise ValueError("Item must be a non-empty dictionary")

        with self._lock:
            if len(self._queue) >= self.MAX_QUEUE_SIZE:
                error_msg = f"Queue is full (max {self.MAX_QUEUE_SIZE} items). Please clear some items first."
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Adding item to queue: {item.get('url')} (Title: {item.get('title')})")
            self._queue.append(item)
        self._notify_listeners_safe()

    def remove_item(self, item: Dict[str, Any]):
        """Remove an item from the queue."""
        changed = False
        with self._lock:
            if item in self._queue:
                logger.info(f"Removing item from queue: {item.get('url')} (Status: {item.get('status')})")
                self._queue.remove(item)
                changed = True
        if changed:
            self._notify_listeners_safe()

    def swap_items(self, index1: int, index2: int):
        """Swap two items in the queue."""
        changed = False
        with self._lock:
            if 0 <= index1 < len(self._queue) and 0 <= index2 < len(self._queue):
                logger.debug(f"Swapping queue items at indices {index1} and {index2}")
                self._queue[index1], self._queue[index2] = (
                    self._queue[index2],
                    self._queue[index1],
                )
                changed = True
        if changed:
            self._notify_listeners_safe()

    # NOTE: find_next_downloadable was removed as it's deprecated and could cause race conditions.
    # Always use claim_next_downloadable() for atomic claim operations.

    def update_scheduled_items(self, now) -> int:
        """
        Update all items whose scheduled time has been reached.

        This transitions items from "Scheduled (HH:MM)" → "Queued" when their
        scheduled_time is in the past, while keeping all mutations localized
        inside QueueManager to avoid external locking on its internals.

        Args:
            now: Current datetime (typically `datetime.now()`).

        Returns:
            int: Number of items that were updated.
        """
        updated = 0
        with self._lock:
            for item in self._queue:
                if item.get("scheduled_time") and str(item.get("status", "")).startswith(
                    "Scheduled"
                ):
                    if now >= item["scheduled_time"]:
                        logger.info(f"Scheduled time reached for item: {item.get('title')}")
                        item["status"] = "Queued"
                        item["scheduled_time"] = None
                        updated += 1
        if updated:
            self._notify_listeners_safe()
        return updated

    def claim_next_downloadable(self) -> Optional[Dict[str, Any]]:
        """
        Atomically find the next 'Queued' item and mark it as 'Allocated' (or 'Downloading').
        This prevents race conditions where multiple threads might pick the same item.

        Also cleans up stale "Allocating" items that have been stuck for too long.
        """
        with self._lock:
            # First, check for stale "Allocating" items (stuck for > 60 seconds)
            stale_timeout = timedelta(seconds=60)
            now = datetime.now()

            for item in self._queue:
                if item["status"] == "Allocating":
                    allocated_time = item.get("_allocated_at")
                    if allocated_time:
                        if now - allocated_time > stale_timeout:
                            logger.warning(
                                f"Found stale 'Allocating' item, resetting to Queued: "
                                f"{item.get('title', item['url'])}"
                            )
                            item["status"] = "Queued"
                            item.pop("_allocated_at", None)

            # Now find next queued item
            for item in self._queue:
                if item["status"] == "Queued":
                    logger.debug(f"Claiming next downloadable item: {item.get('title')}")
                    item["status"] = "Allocating"  # Temporary status
                    item["_allocated_at"] = now
                    return item
        return None

    def any_in_status(self, status: str) -> bool:
        """Check if any item has the given status."""
        with self._lock:
            return any(item["status"] == status for item in self._queue)

    def any_downloading(self) -> bool:
        """Check if any item is currently downloading."""
        with self._lock:
            return any(
                item["status"] in ("Downloading", "Allocating", "Processing")
                for item in self._queue
            )
