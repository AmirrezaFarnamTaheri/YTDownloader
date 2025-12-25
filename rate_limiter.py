"""
Rate limiter for application actions.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class RateLimiter:
    """Simple rate limiter based on time intervals."""

    def __init__(self, limit_seconds: float = 0.5):
        self._last_action_time = 0.0
        self._limit_seconds = limit_seconds
        self._lock = threading.Lock()

    def check(self) -> bool:
        """
        Check if the action is allowed.
        Updates the last action time if allowed.
        Thread-safe implementation using lock.

        Returns:
            bool: True if action is allowed, False if rate limited.
        """
        with self._lock:
            now = time.time()
            if now - self._last_action_time < self._limit_seconds:
                logger.debug(
                    "Rate limit hit: %.2fs since last action (limit=%.2fs)",
                    now - self._last_action_time,
                    self._limit_seconds,
                )
                return False
            self._last_action_time = now
            logger.debug("Rate limiter allow after %.2fs", self._limit_seconds)
            return True
