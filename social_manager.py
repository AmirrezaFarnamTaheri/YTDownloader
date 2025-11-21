import logging
import time
import os

logger = logging.getLogger(__name__)

class SocialManager:
    """
    Manages Social integrations (Discord RPC).
    """

    def __init__(self, client_id: str = "123456789012345678"): # Placeholder ID
        self.client_id = client_id
        self.rpc = None
        self.connected = False

    def connect(self):
        if self.connected: return
        try:
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
             # Try to connect once?
             # self.connect()
             return

        try:
            self.rpc.update(
                state=state,
                details=details,
                large_image="logo", # key in discord app assets
                large_text="StreamCatch",
                start=time.time()
            )
        except Exception as e:
            logger.debug(f"Failed to update RPC: {e}")
            self.connected = False # Assume disconnected

    def close(self):
        if self.rpc:
            try:
                self.rpc.close()
            except: pass
        self.connected = False
