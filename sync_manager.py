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

        logger.info(f"Starting data export to: {output_path}")

        data = {
            "timestamp": datetime.now().isoformat(),
            "config": ConfigManager.load_config(),
            "history": HistoryManager.get_history(limit=10000),
        }

        try:
            # Atomic write using temp file and rename
            import tempfile
            dir_name = os.path.dirname(output_path) or "."
            os.makedirs(dir_name, exist_ok=True)

            fd, temp_path = tempfile.mkstemp(
                dir=dir_name, prefix=".export_tmp_", suffix=".json"
            )

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic rename
                if os.name == "nt" and os.path.exists(output_path):
                    os.remove(output_path)

                os.replace(temp_path, output_path)
                logger.info(f"Data exported to {output_path}")
                return output_path
            except Exception:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise

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

        logger.info(f"Starting data import from: {input_path}")

        if not os.path.exists(input_path):
            error_msg = f"Import file not found: {input_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            # Ensure DB is initialized before importing
            HistoryManager.init_db()

            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Import Config
            if "config" in data:
                logger.debug(f"Importing configuration with {len(data['config'])} keys")
                ConfigManager.save_config(data["config"])

            # Import History
            if "history" in data:
                count = 0
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
                    count += 1
                logger.info(f"Imported {count} history entries")

            logger.info(f"Data imported successfully from {input_path}")

        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise
