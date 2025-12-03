"""
Social media integration manager (Discord Rich Presence).

Handles connection to Discord RPC to display current status.
"""

import logging
import os
import threading
import time

from pypresence import Presence

logger = logging.getLogger(__name__)


class SocialManager:
    """Manages Discord Rich Presence."""

    def __init__(self):
        self.rpc = None
        self.connected = False
        # Get client ID from env or use default/dummy
        self._client_id = os.environ.get("DISCORD_CLIENT_ID", "123456789012345678")
        self._lock = threading.Lock()

    def connect(self):
        """Connect to Discord RPC."""
        # Simple check to avoid trying if ID is dummy/invalid
        if (
            not self._client_id
            or self._client_id == "123456789012345678"
            or not self._client_id.isdigit()
        ):
            # Silent fail or log debug
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
                )
            except Exception as e:
                logger.warning("Failed to update Discord activity: %s", e)
                self.connected = False

    def close(self):
        """Close the RPC connection."""
        with self._lock:
            if self.rpc:
                try:
                    self.rpc.close()
                except Exception:
                    pass
                self.connected = False
