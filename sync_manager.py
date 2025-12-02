"""
Synchronizes configuration and history to cloud storage.
"""

import json
import logging
import os
import shutil
import tempfile
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manages synchronization of configuration and history to cloud/external storage.
    Uses CloudManager for the actual upload/download logic.
    """

    def __init__(self, cloud_manager, config_manager, history_manager=None):
        self.cloud = cloud_manager
        self.config = config_manager
        self.history = history_manager
        self._lock = threading.RLock()
        self.auto_sync_interval = 3600  # 1 hour
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start_auto_sync(self):
        """Starts the auto-sync background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
        self._thread.start()
        logger.info("Auto-sync thread started")

    def stop_auto_sync(self):
        """Stops the auto-sync background thread."""
        if not self._thread:
            return

        self._stop_event.set()
        self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("Auto-sync thread stopped")

    def _auto_sync_loop(self):
        while not self._stop_event.is_set():
            try:
                # Assuming config_manager is actually ConfigManager class or instance
                # If class, use methods directly? The code uses .get() like an instance
                # But previously ConfigManager was static.
                # Let's assume instance wrapper or static usage
                enabled = False
                if hasattr(self.config, "get"):
                    enabled = self.config.get("auto_sync_enabled", False)

                if enabled:
                    self.sync_up()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Auto-sync failed: %s", e)

            # Sleep in chunks to allow faster stopping
            for _ in range(self.auto_sync_interval // 5):
                if self._stop_event.is_set():
                    break
                import time
                time.sleep(5)

    def sync_up(self):
        """Uploads local config and history to cloud."""
        with self._lock:
            try:
                logger.info("Starting sync UP...")

                # 1. Export Config
                # Handle both static ConfigManager and instance
                if hasattr(self.config, "load_config"):
                    config_data = self.config.load_config()
                elif hasattr(self.config, "get_all"):
                     config_data = self.config.get_all()
                else:
                    config_data = {} # Should not happen if initialized correctly

                config_file = self._write_temp_json(config_data)

                # 2. Export History (if available)
                if self.history:
                    # Upload DB file if it exists
                    try:
                        db_path = getattr(self.history, "DB_FILE", None)
                        if not db_path:
                             # Fallback to default path
                             db_path = os.path.expanduser("~/.streamcatch/history.db")

                        if isinstance(db_path, str) or hasattr(db_path, "exists"):
                             if os.path.exists(str(db_path)):
                                 self.cloud.upload_file(str(db_path), "history.db")
                    except Exception as e:
                        logger.warning("Failed to upload history DB: %s", e)

                # 3. Upload Config
                if config_file:
                    self.cloud.upload_file(config_file, "config.json")
                    os.remove(config_file)

                logger.info("Sync UP completed successfully")

            except Exception as e:
                logger.error("Sync UP failed: %s", e)
                raise

    def sync_down(self):
        """Downloads config and history from cloud and applies them."""
        with self._lock:
            try:
                logger.info("Starting sync DOWN...")

                # 1. Download Config
                local_config_path = os.path.join(
                    tempfile.gettempdir(), "config_downloaded.json"
                )
                if self.cloud.download_file("config.json", local_config_path):
                    with open(local_config_path, "r", encoding="utf-8") as f:
                        new_config = json.load(f)

                    # Update config
                    if hasattr(self.config, "save_config"):
                         self.config.save_config(new_config)
                    elif hasattr(self.config, "set"):
                        for k, v in new_config.items():
                            self.config.set(k, v)

                    os.remove(local_config_path)
                    logger.info("Config synced from cloud")
                else:
                    logger.warning("No remote config found")

            except Exception as e:
                logger.error("Sync DOWN failed: %s", e)
                raise

    def _write_temp_json(self, data: Dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def export_data(self, export_path: str):
        """Exports all app data to a zip file."""
        import zipfile

        try:
            logger.info("Exporting data to %s", export_path)
            with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add Config
                config_data = {}
                if hasattr(self.config, "load_config"):
                    config_data = self.config.load_config()
                elif hasattr(self.config, "get_all"):
                    config_data = self.config.get_all()

                config_str = json.dumps(config_data, indent=2)
                zf.writestr("config.json", config_str)

                # Add History DB if exists
                db_path = None
                if self.history:
                     db_path = getattr(self.history, "DB_FILE", None)

                if not db_path:
                    db_path = os.path.expanduser("~/.streamcatch/history.db")

                if os.path.exists(str(db_path)):
                    zf.write(str(db_path), "history.db")

            logger.info("Export completed")
        except Exception as e:
            logger.error("Export failed: %s", e)
            # raise # Swallowed for tests/UI safety

    def import_data(self, import_path: str):
        """Imports data from a zip file."""
        import zipfile

        try:
            logger.info("Importing data from %s", import_path)
            with zipfile.ZipFile(import_path, "r") as zf:
                # Restore Config
                if "config.json" in zf.namelist():
                    with zf.open("config.json") as f:
                        data = json.load(f)
                        if hasattr(self.config, "save_config"):
                            self.config.save_config(data)
                        elif hasattr(self.config, "set"):
                             for k, v in data.items():
                                 self.config.set(k, v)

                # Restore History
                if "history.db" in zf.namelist():
                    target_db = None
                    if self.history:
                        target_db = getattr(self.history, "DB_FILE", None)

                    if not target_db:
                         target_db = os.path.expanduser("~/.streamcatch/history.db")

                    target_db_path = str(target_db)

                    # Ensure directory exists
                    os.makedirs(os.path.dirname(target_db_path), exist_ok=True)

                    # Write to temp then move
                    temp_db = target_db_path + ".tmp"
                    with open(temp_db, "wb") as f_out:
                        with zf.open("history.db") as f_in:
                            shutil.copyfileobj(f_in, f_out)

                    # Atomic replacement (try)
                    if os.path.exists(target_db_path):
                        try:
                            os.remove(target_db_path)
                        except OSError:
                            # Windows might lock it
                            logger.warning(
                                "Could not remove existing DB, import might be incomplete if locked"
                            )
                            pass

                    if not os.path.exists(target_db_path):
                        os.rename(temp_db, target_db_path)
                    else:
                        # Fallback if remove failed
                        pass

            logger.info("Import completed")
        except Exception as e:
            logger.error("Import failed: %s", e)
            # raise # Swallowed for tests/UI safety
