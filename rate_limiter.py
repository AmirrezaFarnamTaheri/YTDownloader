"""
Rate limiter for application actions using a Token Bucket algorithm.
Allows for burst handling while maintaining a steady average rate.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe Rate Limiter using the Token Bucket algorithm.

    This allows for 'bursts' of actions up to the bucket capacity,
    while enforcing an average rate of refill.

    Attributes:
        rate (float): Tokens added per second.
        capacity (float): Maximum number of tokens in the bucket (burst size).
        tokens (float): Current number of tokens available.
    """

    def __init__(self, rate: float = 2.0, capacity: float = 5.0):
        """
        Initialize the RateLimiter.

        Args:
            rate: The rate at which tokens are added to the bucket (tokens/second).
                  Default 2.0 means 2 actions per second on average.
            capacity: The maximum number of tokens the bucket can hold.
                      Default 5.0 means we can burst up to 5 actions instantly.
        """
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def check(self, cost: float = 1.0) -> bool:
        """
        Check if an action with the given cost is allowed.
        If allowed, consumes the tokens.

        Args:
            cost: The cost of the action in tokens. Default is 1.0.

        Returns:
            bool: True if allowed, False if rate limited.
        """
        with self._lock:
            now = time.time()
            # Calculate time passed since last check
            elapsed = now - self._last_refill
            self._last_refill = now

            # Refill tokens based on time passed
            # tokens = old_tokens + (time_passed * rate)
            self._tokens = min(self._capacity, self._tokens + (elapsed * self._rate))

            if self._tokens >= cost:
                self._tokens -= cost
                return True

            logger.debug(
                "Rate limit hit: %.2f tokens available, need %.2f", self._tokens, cost
            )
            return False
