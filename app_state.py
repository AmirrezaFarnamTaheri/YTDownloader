import logging
import threading
from datetime import datetime, time
from typing import Any, Dict, Optional

from cloud_manager import CloudManager
from config_manager import ConfigManager
from history_manager import HistoryManager
from queue_manager import QueueManager
from social_manager import SocialManager
from ui_utils import is_ffmpeg_available
from utils import CancelToken

logger = logging.getLogger(__name__)


class AppState:
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

    def __init__(self):
        # Prevent double initialization
        with self._init_lock:
            if self._initialized:
                return

            logger.info("Initializing AppState singleton...")
            self._init_complete = threading.Event()

        self.config = ConfigManager.load_config()
        self.queue_manager = QueueManager()
        self.current_download_item: Optional[Dict[str, Any]] = None
        self.cancel_token: Optional[CancelToken] = None
        self.is_paused = False
        self.video_info: Optional[Dict[str, Any]] = None
        self.ffmpeg_available = is_ffmpeg_available()
        HistoryManager.init_db()

        # Feature flags / States
        self.cinema_mode = False
        self.cloud_manager = CloudManager()
        self.social_manager = SocialManager()
        self.scheduled_time: Optional[time] = None
        self.clipboard_monitor_active = False
        self.last_clipboard_content = ""
        self.shutdown_flag = threading.Event()
        self._video_info_cache: Dict[str, Dict[str, Any]] = {}  # URL -> info
        self._video_info_max_size = 50  # Limit cache size

        # Try connecting to social - but with error isolation
        def _safe_social_connect():
            try:
                logger.debug("Waiting for init to complete before connecting social...")
                self._init_complete.wait(timeout=5.0)  # Wait for init to complete
                logger.debug("Connecting social manager...")
                self.social_manager.connect()
            except Exception as e:
                logger.debug(f"Social manager connection failed (non-critical): {e}")

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
        except Exception as e:
            logger.debug(f"Social manager cleanup error: {e}")

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached video info for URL."""
        return self._video_info_cache.get(url)

    def set_video_info(self, url: str, info: Dict[str, Any]):
        """Cache video info for URL with size limit."""
        # Implement LRU-like behavior
        if len(self._video_info_cache) >= self._video_info_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._video_info_cache))
            del self._video_info_cache[oldest_key]

        self._video_info_cache[url] = info

    def clear_video_info_cache(self):
        """Clear video info cache to free memory."""
        self._video_info_cache.clear()


state = AppState()
