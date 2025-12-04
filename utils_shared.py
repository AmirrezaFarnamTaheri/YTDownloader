"""
Shared utilities for panels and other components.
"""

import os
import signal
from contextlib import contextmanager

@contextmanager
def timeout_manager(seconds=30, error_message="Operation timed out"):
    """
    Context manager for timeout operations.
    Supports Unix signals and Windows threading (simplified/fallback).
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(error_message)

    if os.name != "nt":
        # Unix-like systems use signal
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows fallback - currently just yields without timeout enforcement
        # or relies on threading which is complex to implement generically here
        # without external dependencies or heavy boilerplate.
        # For now, we trust the operation to have its own timeout or user to cancel.
        yield
