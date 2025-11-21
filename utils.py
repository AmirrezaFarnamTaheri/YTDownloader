import time
from typing import Any


class CancelToken:
    """Token for managing download cancellation and pause/resume."""

    def __init__(self):
        self.cancelled = False
        self.is_paused = False

    def cancel(self):
        self.cancelled = True

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def check(self, d: Any = None):
        """
        Checks if the download should be cancelled or paused.
        Accepts an argument 'd' to be compatible with yt-dlp progress hooks.
        """
        if self.cancelled:
            raise Exception("Download cancelled by user.")

        while self.is_paused:
            time.sleep(0.5)
            if self.cancelled:
                raise Exception("Download cancelled by user.")
