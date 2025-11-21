"""Lightweight in-repo clipboard helper used when the external pyperclip package is unavailable."""

from typing import Optional

# In-memory clipboard fallback. This is used in headless environments where
# system clipboards or the external dependency are not available.
_clipboard_cache: Optional[str] = None


def copy(text: str) -> None:
    global _clipboard_cache
    _clipboard_cache = text


def paste() -> str:
    return _clipboard_cache or ""
