import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)


class SocialManager:
    """
    Manages Social integrations (Discord RPC).
    """

    DEFAULT_CLIENT_ID = "123456789012345678"  # Fallback placeholder

    def __init__(self, client_id: Optional[str] = None):
        logger.debug("Initializing SocialManager...")
        # Prefer environment variable, but fall back to legacy placeholder for compatibility/tests
        self.client_id = (
            client_id or os.environ.get("DISCORD_CLIENT_ID") or self.DEFAULT_CLIENT_ID
        )
        self.rpc = None
        self.connected = False

    def connect(self):
        if self.connected:
            logger.debug("Discord RPC already connected.")
            return
        if not self.client_id:
            logger.info(
                "Discord Rich Presence disabled (no DISCORD_CLIENT_ID provided)."
            )
            return
        try:
            logger.debug(
                f"Attempting to connect to Discord RPC with ID: {self.client_id}"
            )
            from pypresence import Presence

            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.connected = True
            logger.info("Connected to Discord RPC.")
        except ImportError:
            logger.warning("pypresence not installed. Social features disabled.")
        except Exception as e:
            logger.warning(f"Failed to connect to Discord RPC: {e}")

    def update_status(self, state: str, details: str = None):
        """Updates the Rich Presence status."""
        if not self.connected:
            if self.rpc:
                logger.debug(
                    "Discord RPC is present but not connected; skipping update."
                )
                return
            # Try to connect on first update to keep caller simple
            self.connect()
            if not self.connected:
                return

        try:
            logger.debug(f"Updating Discord RPC - State: {state}, Details: {details}")
            self.rpc.update(
                state=state,
                details=details,
                large_image="logo",  # key in discord app assets
                large_text="StreamCatch",
                start=time.time(),
            )
        except Exception as e:
            logger.error(f"Failed to update RPC: {e}", exc_info=True)
            self.connected = False  # Assume disconnected

    def close(self):
        logger.debug("Closing SocialManager...")
        if self.rpc:
            try:
                self.rpc.close()
                logger.info("Discord RPC closed.")
            except Exception as exc:
                logger.debug("Failed to close Discord RPC cleanly: %s", exc)
        self.connected = False
