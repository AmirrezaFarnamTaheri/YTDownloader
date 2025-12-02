"""
Queue Manager module for handling download tasks.
Refactored for robustness, event-driven architecture, and better cancellation support.
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from utils import CancelToken

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

        # Condition variable for background workers to wait on
        self._has_work = threading.Condition(self._lock)

        # Listeners for UI updates
        self._listeners: List[Callable[[], None]] = []
        self._listeners_lock = threading.Lock()

        # Map item IDs to their active CancelTokens
        self._cancel_tokens: Dict[str, CancelToken] = {}

    def get_all(self) -> List[Dict[str, Any]]:
        """Get a copy of the current queue."""
        with self._lock:
            return list(self._queue)

    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by its unique ID."""
        with self._lock:
            for item in self._queue:
                if item.get("id") == item_id:
                    return item
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

            # Ensure ID
            if "id" not in item:
                item["id"] = str(uuid.uuid4())

            # Ensure status
            if "status" not in item:
                item["status"] = "Queued"

            logger.info("Adding item to queue: %s (ID: %s)", item.get("title", item.get("url")), item["id"])
            self._queue.append(item)

            # Notify workers that work might be available
            self._has_work.notify_all()

        self._notify_listeners_safe()

    def remove_item(self, item: Dict[str, Any]):
        """Remove an item from the queue and cancel it if running."""
        changed = False
        item_id = item.get("id")

        # First cancel if running
        if item_id:
            self.cancel_item(item_id)

        with self._lock:
            if item in self._queue:
                self._queue.remove(item)
                changed = True
                # Clean up token if any (just in case cancel_item didn't catch it)
                if item_id in self._cancel_tokens:
                    del self._cancel_tokens[item_id]

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

            if updated > 0:
                self._has_work.notify_all()

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

    def wait_for_items(self, timeout: float = 2.0) -> bool:
        """
        Wait until an item is added or status changes to Queued.
        Returns True if notified, False if timed out.
        """
        with self._has_work:
            return self._has_work.wait(timeout)

    # --- Cancellation Handling ---

    def register_cancel_token(self, item_id: str, token: CancelToken):
        """Register a cancel token for a running download."""
        with self._lock:
            self._cancel_tokens[item_id] = token

    def unregister_cancel_token(self, item_id: str):
        """Unregister a cancel token (e.g. when finished)."""
        with self._lock:
            if item_id in self._cancel_tokens:
                del self._cancel_tokens[item_id]

    def cancel_item(self, item_id: str):
        """Request cancellation of a specific item."""
        with self._lock:
            token = self._cancel_tokens.get(item_id)
            if token:
                logger.info("Cancelling item ID: %s", item_id)
                token.cancel()

            # Update status if in queue but not running yet
            for item in self._queue:
                if item.get("id") == item_id:
                    if item["status"] in ["Queued", "Allocating", "Downloading"]:
                        item["status"] = "Cancelled"
                    break

        self._notify_listeners_safe()
