"""
Rate limiter for application actions.
"""

import time


# pylint: disable=too-few-public-methods
class RateLimiter:
    """Simple rate limiter based on time intervals."""

    def __init__(self, limit_seconds: float = 0.5):
        self._last_action_time = 0.0
        self._limit_seconds = limit_seconds

    def check(self) -> bool:
        """
        Check if the action is allowed.
        Updates the last action time if allowed.
        """
        now = time.time()
        if now - self._last_action_time < self._limit_seconds:
            return False
        self._last_action_time = now
        return True
