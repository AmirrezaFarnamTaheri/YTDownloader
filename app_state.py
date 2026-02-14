"""
Application State Management.

This module provides the `AppState` singleton which manages the global state
of the application, including configuration, queue management, services, and
feature flags.
"""

import logging
import threading
from collections import OrderedDict
from datetime import time
from typing import Any

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
    _init_lock = threading.RLock()  # Use RLock for consistency and safety

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
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    _initialized: bool

    def __init__(self) -> None:  # pylint: disable=too-many-statements
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
        self.current_download_item: dict[str, Any] | None = None
        self.cancel_token: CancelToken | None = None
        self.is_paused = False
        self.video_info: dict[str, Any] | None = None

        self.ffmpeg_available = False  # Updated in background

        self.history_manager = HistoryManager()  # Instance created, DB init later

        # Feature flags / States
        self.cinema_mode = False
        self.cloud_manager = CloudManager()
        self.social_manager = SocialManager()

        # Instantiate SyncManager with dependencies to avoid circular imports
        self.sync_manager = SyncManager(
            self.cloud_manager, self.config, history_manager=self.history_manager
        )

        self.scheduled_time: time | None = None
        self.clipboard_monitor_active = self.config.get(
            "clipboard_monitor_enabled", False
        )
        self.last_clipboard_content = ""
        self.shutdown_flag = threading.Event()

        # New Feature Flags
        theme_mode_raw = str(self.config.get("theme_mode", "System")).strip().lower()
        self.high_contrast = bool(
            self.config.get("high_contrast", False)
            or theme_mode_raw in {"high contrast", "high_contrast", "high-contrast"}
        )
        self.config["high_contrast"] = self.high_contrast
        self.compact_mode = self.config.get("compact_mode", False)

        # Use OrderedDict for proper LRU cache implementation
        self._video_info_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._video_info_max_size = self.config.get("metadata_cache_size", 50)

        # Background Initialization of heavy components
        def _background_init():
            # 1. FFmpeg Check (Warms cache)
            self.ffmpeg_available = is_ffmpeg_available()
            logger.info("FFmpeg available: %s", self.ffmpeg_available)

            # 2. Database Init
            try:
                HistoryManager.init_db()
                logger.info("History database initialized.")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to initialize history database: %s", e)

            # 3. Social Manager
            try:
                # Wait briefly for main loop to be ready if needed,
                # but we are in init so it's fine.
                logger.debug("Connecting social manager...")
                self.social_manager.connect()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.debug("Social manager connection failed (non-critical): %s", e)

        threading.Thread(
            target=_background_init, daemon=True, name="AppStateInit"
        ).start()

        self._initialized = True
        self._init_complete.set()
        logger.info("AppState initialization complete")

    def cleanup(self) -> None:
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
            logger.debug("Cleaning up queue manager...")
            if self.queue_manager:
                self.queue_manager.cancel_all()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Queue manager cleanup error: %s", e)

        try:
            logger.debug("Saving configuration...")
            ConfigManager.save_config(self.config)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Config save error during cleanup: %s", e)

        logger.info("AppState cleanup complete")

    def get_video_info(self, url: str) -> dict[str, Any] | None:
        """Get cached video info for URL with LRU tracking."""
        info = self._video_info_cache.get(url)
        if info:
            logger.debug("Cache hit for video info: %s", url)
            # Move to end to mark as recently used (LRU)
            self._video_info_cache.move_to_end(url)
        else:
            logger.debug("Cache miss for video info: %s", url)
        return info

    def set_video_info(self, url: str, info: dict[str, Any]) -> None:
        """Cache video info for URL with proper LRU eviction."""
        # If URL already exists, remove it first so it goes to the end
        if url in self._video_info_cache:
            del self._video_info_cache[url]

        # Evict least recently used entry if cache is full
        if len(self._video_info_cache) >= self._video_info_max_size:
            # Remove oldest (least recently used) entry from the beginning
            oldest_key = next(iter(self._video_info_cache))
            logger.debug(
                "Evicting least recently used video info cache entry: %s", oldest_key
            )
            del self._video_info_cache[oldest_key]

        logger.debug("Caching video info for: %s", url)
        self._video_info_cache[url] = info

    def clear_video_info_cache(self) -> None:
        """Clear video info cache to free memory."""
        logger.debug("Clearing all video info cache")
        self._video_info_cache.clear()


state = AppState()
