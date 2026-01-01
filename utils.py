"""
General utility classes and functions.
"""

import threading
import time
from typing import Any


class CancelToken:
    """Token for managing download cancellation and pause/resume with thread safety."""

    def __init__(self, pause_timeout: float = 300.0):
        """
        Initialize CancelToken.

        Args:
            pause_timeout: Maximum time (in seconds) to wait in paused state before auto-resuming.
                          Default is 5 minutes. Set to 0 for infinite wait (not recommended).
        """
        self._cancelled: bool = False
        self._is_paused: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._pause_timeout: float = pause_timeout

    def cancel(self) -> None:
        """Set the cancellation flag in a thread-safe manner."""
        with self._lock:
            self._cancelled = True

    def pause(self) -> None:
        """Set the pause flag in a thread-safe manner."""
        with self._lock:
            self._is_paused = True

    def resume(self) -> None:
        """Clear the pause flag in a thread-safe manner."""
        with self._lock:
            self._is_paused = False

    @property
    def cancelled(self) -> bool:
        """Thread-safe read of cancellation status."""
        with self._lock:
            return self._cancelled

    @property
    def is_paused(self) -> bool:
        """Thread-safe read of pause status."""
        with self._lock:
            return self._is_paused

    def check(self, _d: Any = None) -> None:
        """
        Checks if the download should be cancelled or paused.
        Accepts an argument '_d' to be compatible with yt-dlp progress hooks (unused).

        Raises:
            InterruptedError: If download is cancelled or pause timeout exceeded.
        """
        # pylint: disable=unused-argument
        if self.cancelled:
            raise InterruptedError("Download Cancelled by user")

        if self.is_paused:
            pause_start = time.time()
            while self.is_paused:
                time.sleep(0.5)
                if self.cancelled:
                    raise InterruptedError("Download Cancelled by user")

                # Check for timeout to prevent infinite pause
                if self._pause_timeout > 0:
                    elapsed = time.time() - pause_start
                    if elapsed > self._pause_timeout:
                        # Auto-cancel after timeout to avoid indefinite pause
                        with self._lock:
                            self._is_paused = False
                            self._cancelled = True
                        raise InterruptedError(
                            f"Download Cancelled by pause timeout ({elapsed:.0f}s)."
                        )
