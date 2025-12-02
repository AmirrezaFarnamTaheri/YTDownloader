"""
Queue Manager module for handling download tasks.
Refactored for robustness, event-driven architecture, and better cancellation support.
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

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

    @property
    def has_work_condition(self):
        """Expose condition variable for workers."""
        return self._has_work

    def get_all(self) -> List[Dict[str, Any]]:
        """Get a copy of the current queue."""
        with self._lock:
            # Return shallow copy
            return list(self._queue)

    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by its unique ID."""
        with self._lock:
            for item in self._queue:
                if item.get("id") == item_id:
                    return item
        return None

    def get_item_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get item by its index in the queue."""
        with self._lock:
            if 0 <= index < len(self._queue):
                return self._queue[index]
        return None

    def any_downloading(self) -> bool:
        """Check if any items are currently in a downloading or active state."""
        return self.any_in_status(["Downloading", "Allocating", "Processing"])

    def any_in_status(self, status: Union[str, List[str]]) -> bool:
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
            except Exception as e:  # pylint: disable=broad-exception-caught
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

            logger.info(
                "Adding item to queue: %s (ID: %s)",
                item.get("title", item.get("url")),
                item["id"],
            )
            self._queue.append(item)

            # Notify workers that work might be available
            # Must acquire the condition lock (which is self._lock)
            self._has_work.notify_all()

        self._notify_listeners_safe()

    def update_item_status(
        self, item_id: str, status: str, updates: Optional[Dict[str, Any]] = None
    ):
        """
        Atomically update an item's status and other fields.
        """
        updated = False
        with self._lock:
            for item in self._queue:
                if item.get("id") == item_id:
                    item["status"] = status
                    if updates:
                        item.update(updates)
                    updated = True
                    break

            if updated and status == "Queued":
                self._has_work.notify_all()

        if updated:
            self._notify_listeners_safe()

    def remove_item(self, item: Dict[str, Any]):
        """
        Remove an item from the queue and cancel it if running.
        Atomic operation.
        """
        item_id = item.get("id")
        removed = False

        # If no ID (legacy), fallback to old method
        if not item_id:
            with self._lock:
                if item in self._queue:
                    self._queue.remove(item)
                    removed = True

            if removed:
                self._notify_listeners_safe()
            return

        with self._lock:
            # Find actual item object in queue (in case 'item' is a copy)
            target = None
            for q_item in self._queue:
                if q_item.get("id") == item_id:
                    target = q_item
                    break

            if target:
                # Cancel if running
                token = self._cancel_tokens.get(item_id)
                if token:
                    token.cancel()
                    # Do not delete from token map yet, tasks.py cleans up?
                    # No, tasks.py unregisters on finally.
                    # But if we remove the item from queue, tasks.py might not find it if it looks it up.
                    # Actually tasks.py holds the item object.
                    # Safe to remove from queue list.

                self._queue.remove(target)
                removed = True

        # Notify outside lock to prevent deadlock if listener calls back into queue
        if removed:
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
        # _has_work uses _lock, so we are essentially doing "with _lock: wait()"
        with self._has_work:
            return self._has_work.wait(timeout)

    def notify_workers(self):
        """Notify workers that state has changed."""
        with self._has_work:
            self._has_work.notify_all()

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

            # Update status only if in non-terminal state
            for item in self._queue:
                if item.get("id") == item_id:
                    # Prevent overwriting terminal statuses like 'Completed', 'Error', 'Cancelled'
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
