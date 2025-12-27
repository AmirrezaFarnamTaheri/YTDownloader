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

    def __init__(self):
        self.rpc = None
        self.connected = False
        # Get client ID from env - no default for security
        self._client_id = os.environ.get("DISCORD_CLIENT_ID", "")
        self._lock = threading.Lock()

    def connect(self):
        """Connect to Discord RPC."""
        if Presence is None:
            logger.info("Discord RPC unavailable: pypresence not installed")
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
                logger.info("Connected to Discord RPC")
            # pylint: disable=broad-exception-caught
            except Exception as e:
                logger.warning("Failed to connect to Discord RPC: %s", e)

    def update_activity(self, details: str, state: str, large_image: str = "logo"):
        """Update the rich presence activity."""
        if not self.connected:
            return

        with self._lock:
            try:
                self.rpc.update(
                    details=details,
                    state=state,
                    large_image=large_image,
                    large_text="StreamCatch",
                    start=time.time(),
                    # pylint: disable=broad-exception-caught
                )
            # pylint: disable=broad-exception-caught
            except Exception as e:
                logger.warning("Failed to update Discord activity: %s", e)
                self.connected = False

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
