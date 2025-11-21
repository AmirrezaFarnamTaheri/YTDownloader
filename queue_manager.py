import threading
from typing import List, Dict, Any, Optional, Callable
import logging

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
                logger.error(f"Error in queue listener: {e}")

    def add_item(self, item: Dict[str, Any]):
        """
        Add an item to the queue.

        Raises:
            ValueError: If queue is at maximum capacity.
        """
        with self._lock:
            if len(self._queue) >= self.MAX_QUEUE_SIZE:
                raise ValueError(f"Queue is full (max {self.MAX_QUEUE_SIZE} items). Please clear some items first.")
            self._queue.append(item)
        self._notify_listeners_safe()

    def remove_item(self, item: Dict[str, Any]):
        """Remove an item from the queue."""
        changed = False
        with self._lock:
            if item in self._queue:
                self._queue.remove(item)
                changed = True
        if changed:
            self._notify_listeners_safe()

    def swap_items(self, index1: int, index2: int):
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

    # NOTE: find_next_downloadable was removed as it's deprecated and could cause race conditions.
    # Always use claim_next_downloadable() for atomic claim operations.

    def claim_next_downloadable(self) -> Optional[Dict[str, Any]]:
        """
        Atomically find the next 'Queued' item and mark it as 'Allocated' (or 'Downloading').
        This prevents race conditions where multiple threads might pick the same item.
        """
        with self._lock:
            for item in self._queue:
                if item["status"] == "Queued":
                    item["status"] = "Allocating"  # Temporary status
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
