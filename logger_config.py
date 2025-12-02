"""
Logging configuration module.
"""

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging():
    """Setup comprehensive logging configuration."""
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers to prevent duplication
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Console Handler (INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # File Handler (DEBUG+, Rotating)
    # Log to both local directory (for easy access) and user home (persistence)
    # Use fallback if home is not writable (mobile/sandbox)
    home_log = Path.home() / ".streamcatch" / "app.log"
    try:
        home_log.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to local
        home_log = Path("app.log")

    log_files = [Path("ytdownloader.log"), home_log]

    # Deduplicate paths if home == local
    log_files = list(set(log_files))

    for log_file in log_files:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(log_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup log file {log_file}: {e}", file=sys.stderr)

    logging.info("Logging initialized successfully.")
