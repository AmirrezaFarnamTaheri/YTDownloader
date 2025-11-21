import json
import os
import logging
from pathlib import Path
from datetime import datetime
from config_manager import ConfigManager
from history_manager import HistoryManager

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages data synchronization (Export/Import)."""

    EXPORT_FILE = "streamcatch_data.json"

    @staticmethod
    def export_data(output_path: str = None) -> str:
        """
        Exports configuration and history to a JSON file.
        Returns the path of the exported file.
        """
        if output_path is None:
            output_path = str(Path.home() / SyncManager.EXPORT_FILE)

        data = {
            "timestamp": datetime.now().isoformat(),
            "config": ConfigManager.load_config(),
            "history": HistoryManager.get_history(limit=10000),
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            logger.info(f"Data exported to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise

    @staticmethod
    def import_data(input_path: str = None):
        """
        Imports configuration and history from a JSON file.
        """
        if input_path is None:
            input_path = str(Path.home() / SyncManager.EXPORT_FILE)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Import file not found: {input_path}")

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Import Config
            if "config" in data:
                ConfigManager.save_config(data["config"])

            # Import History
            if "history" in data:
                for item in data["history"]:
                    HistoryManager.add_entry(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        output_path=item.get("output_path", ""),
                        format_str=item.get("format_str", ""),
                        status=item.get("status", "Imported"),
                        file_size=item.get("file_size", "N/A"),
                        file_path=item.get("file_path"),
                    )

            logger.info(f"Data imported from {input_path}")

        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise
