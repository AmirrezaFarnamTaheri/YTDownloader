"""
Queue Manager module for handling download tasks.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Thread-safe manager for the download queue.

    Status Lifecycle:
    - "Queued" -> "Allocating" -> "Downloading" -> "Processing" -> "Completed"
    - "Queued" -> "Allocating" -> "Downloading" -> "Error"
    - "Queued" -> "Allocating" -> "Downloading" -> "Cancelled"
    - "Scheduled (HH:MM)" -> "Queued" (when time reached)
    """

    MAX_QUEUE_SIZE = 1000

    def __init__(self):
        self._queue: List[Dict[str, Any]] = []
        # Re-entrant lock for queue operations
        self._lock = threading.RLock()
        self._listeners: List[Callable[[], None]] = []
        self._listeners_lock = threading.Lock()

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
        with self._listeners_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]):
        """Remove a listener callback."""
        with self._listeners_lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _notify_listeners_safe(self):
        """Notify listeners safely without holding the queue lock."""
        # Snapshot listeners
        with self._listeners_lock:
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener()
            except Exception as e:
                logger.error("Error in queue listener: %s", e)

    def add_item(self, item: Dict[str, Any]):
        """Add an item to the queue."""
        if not isinstance(item, dict):
            raise ValueError("Item must be a dictionary")

        with self._lock:
            if len(self._queue) >= self.MAX_QUEUE_SIZE:
                raise ValueError("Queue is full")

            logger.info("Adding item: %s", item.get("title", item.get("url")))
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

    def update_scheduled_items(self, now: datetime) -> int:
        """Transition scheduled items to Queued if time reached."""
        updated = 0
        with self._lock:
            for item in self._queue:
                status = str(item.get("status", ""))
                if status.startswith("Scheduled") and item.get("scheduled_time"):
                    if now >= item["scheduled_time"]:
                        item["status"] = "Queued"
                        item["scheduled_time"] = None
                        updated += 1

        if updated:
            self._notify_listeners_safe()
        return updated

    def claim_next_downloadable(self) -> Optional[Dict[str, Any]]:
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
                        item.pop("_allocated_at", None)

            # Find next
            for item in self._queue:
                if item["status"] == "Queued":
                    item["status"] = "Allocating"
                    item["_allocated_at"] = now
                    return item
        return None
