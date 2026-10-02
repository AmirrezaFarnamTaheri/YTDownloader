"""Locations of the mutable per-user application data.

StreamCatch keeps its configuration, download history, and log file in a single
data directory (``~/.streamcatch`` by default). The directory can be redirected
with the ``STREAMCATCH_DATA_DIR`` environment variable, which is what makes a
portable install possible and lets the test suite run without touching the
developer's real configuration, history, or logs.

``data_dir()`` reads the environment on every call, so a process — or a test
session — must set the variable *before* importing the modules that own a file:
``ConfigManager.CONFIG_FILE``, ``HistoryManager.DB_FILE``, and the logger resolve
their path once at import (application startup). Changing the variable while the
application is running does not move existing files.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

#: Environment variable that relocates the per-user data directory.
DATA_DIR_ENV = "STREAMCATCH_DATA_DIR"

#: Default directory name inside the user's home folder.
DEFAULT_DIR_NAME = ".streamcatch"


def data_dir() -> Path:
    """Return the directory holding configuration, history, and logs.

    ``STREAMCATCH_DATA_DIR`` wins when it is set to a non-empty value; an
    invalid value (for example an unwritable path) is still returned verbatim so
    the caller's own error handling and fallbacks apply.
    """
    override = os.environ.get(DATA_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    try:
        return Path.home() / DEFAULT_DIR_NAME
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Could not resolve the home directory: %s", exc)
        return Path(DEFAULT_DIR_NAME)


def data_file(name: str) -> Path:
    """Return the path of ``name`` inside the data directory."""
    return data_dir() / name
