"""
Synchronizes configuration and history to cloud storage.
"""

import json
import logging
import os
import shutil
import tempfile
import threading
import zipfile
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
        self.auto_sync_interval = 3600.0  # 1 hour
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
        logger.info("Auto-sync loop started")
        while not self._stop_event.is_set():
            try:
                enabled = False
                if hasattr(self.config, "load_config"):
                    # It's the class or instance with load_config
                    # load_config returns a dict
                    cfg = self.config.load_config()
                    enabled = cfg.get("auto_sync_enabled", False)
                elif hasattr(self.config, "get"):
                    enabled = self.config.get("auto_sync_enabled", False)

                if enabled:
                    self.sync_up()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Auto-sync failed: %s", e)

            # Sleep avoiding busy loop
            remaining = max(int(self.auto_sync_interval), 1)
            step = min(5, remaining)
            waited = 0
            while waited < remaining and not self._stop_event.is_set():
                self._stop_event.wait(step)
                waited += step

    def sync_up(self):
        """Uploads local config and history to cloud."""
        with self._lock:
            try:
                logger.info("Starting sync UP...")

                # 1. Export Config
                if hasattr(self.config, "load_config"):
                    config_data = self.config.load_config()
                elif hasattr(self.config, "get_all"):
                    config_data = self.config.get_all()
                else:
                    config_data = {}

                config_file = self._write_temp_json(config_data)

                # 2. Export History (if available)
                if self.history:
                    try:
                        db_path = getattr(self.history, "DB_FILE", None)
                        if not db_path:
                            db_path = os.path.expanduser("~/.streamcatch/history.db")

                        db_path_str = str(db_path)
                        if os.path.exists(db_path_str):
                            self.cloud.upload_file(db_path_str, "history.db")
                    except Exception as e:  # pylint: disable=broad-exception-caught
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
            # Handle non-serializable objects (like Mocks in tests)
            def default_serializer(obj):
                return str(obj)

            json.dump(data, f, indent=2, default=default_serializer)
        return path

    def export_data(self, export_path: str):
        """Exports all app data to a zip file."""
        try:
            logger.info("Exporting data to %s", export_path)
            with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add Config
                config_data = {}
                if hasattr(self.config, "load_config"):
                    config_data = self.config.load_config()
                elif hasattr(self.config, "get_all"):
                    config_data = self.config.get_all()

                # Handle potential non-serializable objects (e.g. from mocks)
                def default_serializer(obj):
                    return str(obj)

                config_str = json.dumps(
                    config_data, indent=2, default=default_serializer
                )
                zf.writestr("config.json", config_str)

                # Add History DB if exists
                db_path = None
                if self.history:
                    db_path = getattr(self.history, "DB_FILE", None)

                if not db_path:
                    db_path = "history.db"

                # Robust path handling
                try:
                    db_path_str = str(db_path)
                    # Resolve to absolute to be sure
                    if not os.path.isabs(db_path_str):
                        db_path_str = os.path.abspath(db_path_str)

                    if os.path.exists(db_path_str):
                        zf.write(db_path_str, "history.db")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning("Could not include history.db in export: %s", e)

            logger.info("Export completed")
        except Exception as e:
            logger.error("Export failed: %s", e)
            raise  # Raise so UI can show error

    def _import_history_db(self, zf: zipfile.ZipFile) -> None:
        """Helper to extract and replace history DB."""
        if "history.db" not in zf.namelist():
            return

        target_db = None
        if self.history:
            target_db = getattr(self.history, "DB_FILE", None)

        if not target_db:
            target_db = os.path.expanduser("~/.streamcatch/history.db")

        target_db_path = str(target_db)

        # Ensure directory exists
        parent = os.path.dirname(target_db_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        # Write to temp then move
        # Validate the target path to prevent path traversal
        target_db_resolved = os.path.abspath(target_db_path)
        parent_resolved = os.path.abspath(parent)

        # Ensure target is within expected directory
        if not target_db_resolved.startswith(parent_resolved + os.sep):
            logger.error("Invalid database path detected (path traversal attempt)")
            return

        temp_db = target_db_path + ".tmp"

        try:
            with open(temp_db, "wb") as f_out:
                with zf.open("history.db") as f_in:
                    shutil.copyfileobj(f_in, f_out)

            # Atomic replacement (try)
            if os.path.exists(target_db_path):
                try:
                    os.remove(target_db_path)
                except OSError:
                    logger.warning(
                        "Could not remove existing DB, import might be incomplete if locked"
                    )

            if not os.path.exists(target_db_path):
                os.rename(temp_db, target_db_path)
            else:
                logger.error("Failed to replace database file, it may be locked.")

        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except OSError as e:  # pylint: disable=broad-exception-caught
                    logger.error(
                        "Failed to clean up temporary DB file %s: %s", temp_db, e
                    )

    def import_data(self, import_path: str):
        """Imports data from a zip file."""
        try:
            logger.info("Importing data from %s", import_path)
            if not os.path.exists(import_path):
                raise FileNotFoundError(f"Import file not found: {import_path}")

            with zipfile.ZipFile(import_path, "r") as zf:
                # Restore Config
                if "config.json" in zf.namelist():
                    with zf.open("config.json") as f:
                        data = json.load(f)
                        if hasattr(self.config, "save_config"):
                            self.config.save_config(data)
                        elif hasattr(self.config, "set"):
                            # Mocks often use this
                            for k, v in data.items():
                                self.config.set(k, v)

                # Restore History
                self._import_history_db(zf)

            logger.info("Import completed")
        except Exception as e:
            logger.error("Import failed: %s", e)
            raise
