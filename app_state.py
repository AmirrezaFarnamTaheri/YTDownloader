"""
Application State Management.

This module provides the `AppState` singleton which manages the global state
of the application, including configuration, queue management, services, and
feature flags.
"""

import logging
import threading
from datetime import time
from typing import Any, Dict, Optional

from cloud_manager import CloudManager
from config_manager import ConfigManager
from history_manager import HistoryManager
from queue_manager import QueueManager
from social_manager import SocialManager
from sync_manager import SyncManager
from ui_utils import is_ffmpeg_available
from utils import CancelToken

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class AppState:
    """
    Singleton class managing the application's global state.

    Attributes:
        config (dict): Application configuration.
        queue_manager (QueueManager): Manages the download queue.
        current_download_item (dict): Currently processing item.
        cancel_token (CancelToken): Token for cancellation.
        is_paused (bool): Global pause state.
        video_info (dict): Current video metadata.
        ffmpeg_available (bool): Status of FFmpeg availability.
        cinema_mode (bool): UI mode flag.
        cloud_manager (CloudManager): Manages cloud integration.
        social_manager (SocialManager): Manages social features.
        sync_manager (SyncManager): Manages data synchronization.
        scheduled_time (time): Scheduled start time.
        clipboard_monitor_active (bool): Clipboard monitoring status.
        last_clipboard_content (str): Last clipboard content.
        shutdown_flag (threading.Event): Flag for shutdown signal.
        high_contrast (bool): Accessibility feature flag.
        compact_mode (bool): UI mode flag.
    """

    _instance = None
    _instance_lock = threading.RLock()  # RLock allows re-entrance
    _init_lock = threading.Lock()  # Separate lock for initialization

    def __new__(cls):
        """
        Thread-safe singleton constructor.

        Double-checked locking pattern to minimize lock contention.
        """
        # First check (unlocked)
        if cls._instance is None:
            with cls._instance_lock:
                # Second check (locked)
                if cls._instance is None:
                    instance = super(AppState, cls).__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):  # pylint: disable=too-many-statements
        # Prevent double initialization
        with self._init_lock:
            if self._initialized:
                logger.debug("AppState already initialized, skipping.")
                return

            logger.info("Initializing AppState singleton...")
            self._init_complete = threading.Event()

        # Initialize core managers
        try:
            self.config = ConfigManager.load_config()
            logger.info("Configuration loaded.")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to load config, using defaults: %s", e)
            self.config = ConfigManager.DEFAULTS.copy()

        self.queue_manager = QueueManager()
        self.current_download_item: Optional[Dict[str, Any]] = None
        self.cancel_token: Optional[CancelToken] = None
        self.is_paused = False
        self.video_info: Optional[Dict[str, Any]] = None

        self.ffmpeg_available = is_ffmpeg_available()
        logger.info("FFmpeg available: %s", self.ffmpeg_available)

        try:
            HistoryManager.init_db()
            logger.info("History database initialized.")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to initialize history database: %s", e)

        # Feature flags / States
        self.cinema_mode = False
        self.cloud_manager = CloudManager()
        self.social_manager = SocialManager()

        # Instantiate SyncManager with dependencies to avoid circular imports
        # Pass HistoryManager class if needed, or instance if refactored
        self.sync_manager = SyncManager(
            self.cloud_manager, self.config, history_manager=HistoryManager
        )

        self.scheduled_time: Optional[time] = None
        self.clipboard_monitor_active = False
        self.last_clipboard_content = ""
        self.shutdown_flag = threading.Event()

        # New Feature Flags
        self.high_contrast = self.config.get("high_contrast", False)
        self.compact_mode = self.config.get("compact_mode", False)

        self._video_info_cache: Dict[str, Dict[str, Any]] = {}  # URL -> info
        self._video_info_max_size = 50  # Limit cache size

        # Try connecting to social - but with error isolation
        def _safe_social_connect():
            try:
                logger.debug("Waiting for init to complete before connecting social...")
                self._init_complete.wait(timeout=5.0)  # Wait for init to complete
                logger.debug("Connecting social manager...")
                self.social_manager.connect()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.debug("Social manager connection failed (non-critical): %s", e)

        threading.Thread(target=_safe_social_connect, daemon=True).start()

        self._initialized = True
        self._init_complete.set()
        logger.info("AppState initialization complete")

    def cleanup(self):
        """Cleanup method for graceful shutdown."""
        logger.info("Cleaning up AppState...")
        self.shutdown_flag.set()

        try:
            logger.debug("Closing social manager...")
            self.social_manager.close()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Social manager cleanup error: %s", e)

        try:
            if self.sync_manager:
                self.sync_manager.stop_auto_sync()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Sync manager cleanup error: %s", e)

        try:
            logger.debug("Closing queue manager...")
            # If QueueManager had cleanup
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Queue manager cleanup error: %s", e)

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached video info for URL."""
        info = self._video_info_cache.get(url)
        if info:
            logger.debug("Cache hit for video info: %s", url)
        else:
            logger.debug("Cache miss for video info: %s", url)
        return info

    def set_video_info(self, url: str, info: Dict[str, Any]):
        """Cache video info for URL with size limit."""
        # Implement LRU-like behavior
        if len(self._video_info_cache) >= self._video_info_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._video_info_cache))
            logger.debug("Evicting oldest video info cache entry: %s", oldest_key)
            del self._video_info_cache[oldest_key]

        logger.debug("Caching video info for: %s", url)
        self._video_info_cache[url] = info

    def clear_video_info_cache(self):
        """Clear video info cache to free memory."""
        logger.debug("Clearing all video info cache")
        self._video_info_cache.clear()


state = AppState()
