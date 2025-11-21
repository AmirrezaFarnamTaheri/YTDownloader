import threading
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class QueueManager:
    """
    Thread-safe manager for the download queue.
    """
    def __init__(self):
        self._queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._listeners = []

    def add_item(self, item: Dict[str, Any]):
        """Add an item to the queue."""
        with self._lock:
            self._queue.append(item)
            self._notify_listeners()

    def remove_item(self, item: Dict[str, Any]):
        """Remove an item from the queue."""
        with self._lock:
            if item in self._queue:
                self._queue.remove(item)
                self._notify_listeners()

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

    def swap_items(self, index1: int, index2: int):
        """Swap two items in the queue."""
        with self._lock:
            if 0 <= index1 < len(self._queue) and 0 <= index2 < len(self._queue):
                self._queue[index1], self._queue[index2] = self._queue[index2], self._queue[index1]
                self._notify_listeners()

    def add_listener(self, listener):
        """Add a listener callback for queue changes."""
        self._listeners.append(listener)

    def _notify_listeners(self):
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                logger.error(f"Error in queue listener: {e}")

    def find_next_downloadable(self) -> Optional[Dict[str, Any]]:
        """
        Find the next item that is ready to download.
        DEPRECATED: Use claim_next_downloadable for atomic operations.
        """
        with self._lock:
            for item in self._queue:
                if item['status'] == 'Queued':
                    return item
        return None

    def claim_next_downloadable(self) -> Optional[Dict[str, Any]]:
        """
        Atomically find the next 'Queued' item and mark it as 'Allocated' (or 'Downloading').
        This prevents race conditions where multiple threads might pick the same item.
        """
        with self._lock:
            for item in self._queue:
                if item['status'] == 'Queued':
                    item['status'] = 'Allocating' # Temporary status
                    return item
        return None

    def any_in_status(self, status: str) -> bool:
        """Check if any item has the given status."""
        with self._lock:
            return any(item['status'] == status for item in self._queue)

    def any_downloading(self) -> bool:
        """Check if any item is currently downloading."""
        with self._lock:
            return any(item['status'] in ('Downloading', 'Allocating', 'Processing') for item in self._queue)
