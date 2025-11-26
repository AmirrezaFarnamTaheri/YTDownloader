import threading
import logging
from typing import Dict, Any, Optional
from datetime import datetime, time

from config_manager import ConfigManager
from queue_manager import QueueManager
from history_manager import HistoryManager
from cloud_manager import CloudManager
from social_manager import SocialManager
from ui_utils import is_ffmpeg_available
from utils import CancelToken

logger = logging.getLogger(__name__)


class AppState:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        """
        Thread-safe singleton constructor.

        Using a dedicated lock here prevents a race where multiple threads
        could see `_instance is None` simultaneously and create more than
        one instance.
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(AppState, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

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

        # Try connecting to social
        threading.Thread(target=self.social_manager.connect, daemon=True).start()

        self._initialized = True


state = AppState()
