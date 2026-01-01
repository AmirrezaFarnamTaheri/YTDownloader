"""
Social media integration manager (Discord Rich Presence).

Handles connection to Discord RPC to display current status.
"""

import logging
import os
import threading
import time

try:  # pragma: no cover - optional dependency
    from pypresence import Presence
except ImportError:
    Presence = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class SocialManager:
    """Manages Discord Rich Presence."""

    MAX_FAILURES = 3

    def __init__(self):
        self.rpc = None
        self.connected = False
        # Get client ID from env - no default for security
        self._client_id = os.environ.get("DISCORD_CLIENT_ID", "")
        self._lock = threading.Lock()
        self.failure_count = 0

    def connect(self):
        """Connect to Discord RPC."""
        if Presence is None:
            logger.info("Discord RPC unavailable: pypresence not installed")
            return

        # Check circuit breaker
        if self.failure_count >= self.MAX_FAILURES:
            return

        # Check if client ID is provided and valid
        if not self._client_id or not self._client_id.isdigit():
            logger.debug("Discord RPC skipped: No valid Client ID provided")
            return

        with self._lock:
            if self.connected:
                return
            try:
                self.rpc = Presence(self._client_id)
                self.rpc.connect()
                self.connected = True
                self.failure_count = 0  # Reset on success
                logger.info("Connected to Discord RPC")
            # pylint: disable=broad-exception-caught
            except Exception as e:
                self.failure_count += 1
                logger.warning("Failed to connect to Discord RPC (Attempt %d/%d): %s",
                             self.failure_count, self.MAX_FAILURES, e)
                if self.failure_count >= self.MAX_FAILURES:
                    logger.warning("Discord RPC disabled due to excessive failures")

    def update_activity(self, details: str, state: str, large_image: str = "logo"):
        """Update the rich presence activity."""
        if not self.connected:
            return

        # Check circuit breaker
        if self.failure_count >= self.MAX_FAILURES:
            return

        with self._lock:
            try:
                self.rpc.update(
                    details=details,
                    state=state,
                    large_image=large_image,
                    large_text="StreamCatch",
                    start=time.time(),
                )
                self.failure_count = 0  # Reset on success
            # pylint: disable=broad-exception-caught
            except Exception as e:
                self.failure_count += 1
                logger.warning("Failed to update Discord activity (Attempt %d/%d): %s",
                             self.failure_count, self.MAX_FAILURES, e)
                # If we fail to update, we might be disconnected
                try:
                    self.connected = False
                    if self.rpc:
                        self.rpc.close()
                except Exception: # pylint: disable=broad-exception-caught
                    pass

                if self.failure_count >= self.MAX_FAILURES:
                    logger.warning("Discord RPC disabled due to excessive failures")

    def close(self):
        """Close the RPC connection."""
        with self._lock:
            if self.rpc:
                # pylint: disable=broad-exception-caught
                try:
                    self.rpc.close()
                except Exception as exc:
                    logger.debug("Failed to close Discord RPC cleanly: %s", exc)
                self.connected = False
