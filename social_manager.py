"""
Social interactions manager (e.g. Discord Rich Presence).
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class SocialManager:
    """
    Manages social interactions (Discord Rich Presence, etc.).
    Fails gracefully if libraries are missing or connection fails.
    """

    def __init__(self):
        self.rpc = None
        self.connected = False
        self._client_id = "123456789012345678"  # Dummy ID for now
        self._lock = threading.Lock()

    def connect(self):
        """Connect to Discord RPC."""
        try:
            from pypresence import Presence

            self.rpc = Presence(self._client_id)
            self.rpc.connect()
            self.connected = True
            logger.info("Connected to Discord Rich Presence")
        except ImportError:
            logger.debug("pypresence not installed, social features disabled")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Failed to connect to Discord RPC: %s", e)
            self.connected = False

    def update_activity(
        self,
        state: str,
        details: Optional[str] = None,
        large_image: Optional[str] = None,
        small_image: Optional[str] = None,
    ):
        """Update user activity."""
        if not self.connected or not self.rpc:
            return

        with self._lock:
            try:
                self.rpc.update(
                    state=state,
                    details=details,
                    large_image=large_image or "logo",
                    small_image=small_image,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.debug("Failed to update activity: %s", e)
                self.connected = False

    def close(self):
        """Close connection."""
        if self.rpc:
            try:
                self.rpc.close()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            self.connected = False
            logger.info("Social manager closed")
