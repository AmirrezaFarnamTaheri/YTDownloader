"""
Logging configuration module.
"""

import logging
import logging.handlers
import sys
import threading
from pathlib import Path

# Module-level flag and lock to prevent re-initialization race conditions
# pylint: disable=invalid-name
_logging_initialized = False
_logging_lock = threading.Lock()


def setup_logging():
    """Setup comprehensive logging configuration."""
    global _logging_initialized  # pylint: disable=global-statement

    # Thread-safe initialization check
    with _logging_lock:
        # Prevent re-initialization which would clear handlers from other modules
        if _logging_initialized:
            return

    log_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers only on first initialization
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
    except Exception:  # pylint: disable=broad-exception-caught
        # Fallback to local
        home_log = Path("app.log")

    log_files = [Path("ytdownloader.log"), home_log]

    # Deduplicate paths while preserving order
    seen = set()
    ordered_unique_log_files = []
    for log_file in log_files:
        if log_file not in seen:
            seen.add(log_file)
            ordered_unique_log_files.append(log_file)
    log_files = ordered_unique_log_files

    for log_file in log_files:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(log_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Failed to setup log file {log_file}: {e}", file=sys.stderr)

    # Set flag after all handlers are configured
    _logging_initialized = True
    logging.info("Logging initialized successfully.")
