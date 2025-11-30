import json
import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Avoid circular dependency by importing CloudManager from state directly or using typing
# But state is imported from app_state which imports CloudManager.
# The issue is `sync_manager` shouldn't import `state` if `app_state` imports `sync_manager`.
# But `app_state` already imports `CloudManager`.
# To break the cycle, `app_state` should import `SyncManager` only inside `__init__` or we pass cloud manager to SyncManager constructor.
# But `SyncManager` uses `state.config` too.
#
# Best approach: Pass dependencies to `SyncManager` constructor and remove `from app_state import state`.

from config_manager import ConfigManager
from history_manager import HistoryManager

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manages synchronization of history and settings with cloud storage.
    Uses a simple "last write wins" strategy based on timestamps for now,
    or merges lists for history.
    """

    SYNC_FILE_NAME = "streamcatch_sync_data.json"

    def __init__(self, cloud_manager: Any, config: Dict[str, Any], output_path: Optional[str] = None):
        self.cloud = cloud_manager
        self.config = config
        self.local_sync_file = Path(tempfile.gettempdir()) / self.SYNC_FILE_NAME
        self.is_syncing = False
        self._lock = threading.Lock()

        # Test hook
        self._output_path = output_path

    def _get_local_data(self) -> Dict[str, Any]:
        """Collect local data to sync."""
        history = HistoryManager.get_history(limit=1000)
        # We use fresh config load
        config = ConfigManager.load_config()
        return {
            "timestamp": time.time(),
            "device_id": self.config.get("device_id", "unknown"),
            "history": history,
            "config": config,
        }

    def sync(self):
        """Perform a full sync (upload and download/merge)."""
        if self.is_syncing:
            logger.warning("Sync already in progress.")
            return

        if not self.cloud.is_authenticated():
            logger.warning("Cannot sync: Not authenticated with cloud.")
            return

        with self._lock:
            self.is_syncing = True
            logger.info("Starting synchronization...")
            try:
                # 1. Download remote data
                remote_data = self._download_remote_data()

                # 2. Merge with local data
                local_data = self._get_local_data()
                merged_data = self._merge_data(local_data, remote_data)

                # 3. Upload merged data
                self._upload_data(merged_data)

                # 4. Apply changes locally
                self._apply_merged_data(merged_data)

                logger.info("Synchronization completed successfully.")
            except Exception as e:
                logger.error(f"Sync failed: {e}", exc_info=True)
            finally:
                self.is_syncing = False

    def _download_remote_data(self) -> Optional[Dict[str, Any]]:
        """Download sync file from cloud."""
        try:
            # Search for sync file
            file_id = self.cloud.get_file_id(self.SYNC_FILE_NAME)
            if not file_id:
                logger.info("No remote sync file found.")
                return None

            # Download content
            content = self.cloud.read_file_content(file_id)
            if content:
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to download remote data: {e}")
        return None

    def _upload_data(self, data: Dict[str, Any]):
        """Upload data to cloud."""
        try:
            # Write to temp file
            with open(self.local_sync_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Upload
            self.cloud.upload_file(str(self.local_sync_file), self.SYNC_FILE_NAME)
        except Exception as e:
            logger.error(f"Failed to upload sync data: {e}")

    def _merge_data(
        self, local: Dict[str, Any], remote: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge local and remote data."""
        if not remote:
            return local

        # Merge history (deduplicate by URL)
        local_history = local.get("history", [])
        remote_history = remote.get("history", [])

        # Create a map of url -> entry, preferring newer timestamps
        merged_history_map = {}

        for entry in remote_history + local_history:
            url = entry.get("url")
            if not url:
                continue
            if url not in merged_history_map:
                merged_history_map[url] = entry
            else:
                # Keep the one with more info or completed status?
                # For simplicity, keep the one that is 'Completed'
                if entry.get("status") == "Completed" and merged_history_map[url].get(
                    "status"
                ) != "Completed":
                    merged_history_map[url] = entry

        merged_history = list(merged_history_map.values())

        # Merge config
        return {
            "timestamp": time.time(),
            "device_id": local["device_id"],
            "history": merged_history,
            "config": local["config"],  # Keep local config for now
        }

    def _apply_merged_data(self, data: Dict[str, Any]):
        """Update local DB with merged history and apply config."""

        # 1. Apply History
        merged_history = data.get("history", [])
        logger.info(f"Applying merged history ({len(merged_history)} items)...")

        # To avoid duplicates without unique constraint in DB (yet), we fetch all existing URLs first
        existing_history = HistoryManager.get_history(limit=10000)
        existing_urls = {item["url"] for item in existing_history}

        added_count = 0
        for item in merged_history:
            url = item.get("url")
            if url and url not in existing_urls:
                try:
                    HistoryManager.add_entry(
                        url=url,
                        title=item.get("title", ""),
                        output_path=item.get("output_path", ""),
                        format_str=item.get("format_str", ""),
                        status=item.get("status", "Synced"),
                        file_size=item.get("file_size", ""),
                        file_path=item.get("file_path"),
                    )
                    added_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add synced item {url}: {e}")

        logger.info(f"Added {added_count} new history items from sync.")

        # 2. Apply Config
        config = data.get("config")
        if config and isinstance(config, dict):
            logger.info("Applying synced configuration...")
            try:
                ConfigManager.save_config(config)
            except Exception as e:
                logger.error(f"Failed to save synced config: {e}")

    def export_data(self, output_path: Optional[str] = None):
        """Export data to a local JSON file."""
        target = output_path or self._output_path
        if not target:
             raise ValueError("Output path not specified")

        data = self._get_local_data()
        try:
            # Atomic write
            temp_path = f"{target}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Atomic replace
            if os.name == 'nt':
                 if os.path.exists(target):
                      os.remove(target)
            os.rename(temp_path, target)
            logger.info(f"Data exported to {target}")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def import_data(self, input_path: Optional[str] = None):
        """Import data from a local JSON file."""
        if not input_path:
             raise ValueError("Input path not specified")

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._apply_merged_data(data)
            logger.info(f"Data imported from {input_path}")
        except Exception as e:
            logger.error(f"Import failed: {e}")
