# pylint: disable=line-too-long,too-many-locals,too-many-arguments,broad-exception-caught,ungrouped-imports,too-many-positional-arguments
"""
yt-dlp wrapper module.

Provides a wrapper around yt-dlp to handle configuration, execution, and error mapping,
ensuring consistent behavior for cancellation and progress reporting.
"""

import logging
import os
import threading
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, cast

import yt_dlp

logger = logging.getLogger(__name__)


class YTDLPWrapper:
    """
    Wrapper around yt-dlp to handle configuration, execution, and error mapping.
    Ensures consistent behavior for cancellation and progress reporting.
    """

    # Bounded LRU cache to prevent unbounded memory growth on large batches
    _SUPPORT_CACHE: "dict[str, bool]" = {}
    _SUPPORT_CACHE_MAX = 500
    _SUPPORT_CACHE_LOCK = threading.Lock()

    def __init__(self, options: dict[str, Any]):
        self.options = options.copy()

    @staticmethod
    def _existing_file_candidate(info: Mapping[str, Any], prepared: str) -> str:
        """Best-effort resolution of the final file after yt-dlp postprocessing."""
        candidates: list[str] = []

        for key in ("filepath", "_filename", "filename"):
            value = info.get(key)
            if isinstance(value, str):
                candidates.append(value)

        requested_downloads = info.get("requested_downloads")
        if isinstance(requested_downloads, list):
            for item in requested_downloads:
                if isinstance(item, dict):
                    for key in ("filepath", "_filename", "filename"):
                        value = item.get(key)
                        if isinstance(value, str):
                            candidates.append(value)

        candidates.append(prepared)
        stem = Path(prepared).with_suffix("")
        for suffix in (
            ".mp4",
            ".mkv",
            ".webm",
            ".m4a",
            ".mp3",
            ".opus",
            ".flac",
            ".wav",
        ):
            candidates.append(str(stem.with_suffix(suffix)))

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate

        parent = Path(prepared).parent
        if parent.exists():
            prefix = stem.name
            matches = [
                path
                for path in parent.glob(f"{prefix}.*")
                if path.is_file() and not path.name.endswith((".part", ".ytdl"))
            ]
            if matches:
                return str(max(matches, key=lambda path: path.stat().st_mtime))

        return prepared

    @staticmethod
    def supports(url: str) -> bool:
        """
        Check if yt-dlp supports the URL by querying its extractors.
        Uses a bounded LRU cache to improve performance on repeated checks.

        Returns True if a non-generic yt-dlp extractor matches the URL,
        False otherwise (allowing fallback to the generic HTTP downloader).
        """
        if not url:
            return False

        cache = YTDLPWrapper._SUPPORT_CACHE
        with YTDLPWrapper._SUPPORT_CACHE_LOCK:
            if url in cache:
                # Move to end for LRU ordering
                cache[url] = cache.pop(url)
                return cache[url]

        supported = True  # safe default
        try:
            # Prefer yt-dlp's own (fast) matching API when available.
            ies = yt_dlp.extractor.gen_extractors()
            for ie in ies:
                try:
                    if ie.suitable(url):
                        if ie.IE_NAME not in ("generic", "Generic"):
                            supported = True
                            break
                        # generic matches but no specific extractor yet; keep searching
                        supported = False
                except Exception:  # pylint: disable=broad-exception-caught
                    # Individual extractors may raise on odd URLs; ignore and continue
                    continue
            else:
                # Loop completed without break => no specific extractor matched
                # (if we found generic earlier supported stays False; else True)
                pass
        except Exception:  # pylint: disable=broad-exception-caught
            supported = True

        with YTDLPWrapper._SUPPORT_CACHE_LOCK:
            cache[url] = supported
            # Evict oldest entries if over capacity
            while len(cache) > YTDLPWrapper._SUPPORT_CACHE_MAX:
                cache.pop(next(iter(cache)))
        return supported

    def download(
        self,
        url: str,
        progress_hook: Callable[[dict[str, Any]], None] | None = None,
        cancel_token: Any | None = None,
        download_item: dict[str, Any] | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute download.

        Args:
            url: The URL to download.
            progress_hook: Callback for progress updates.
            cancel_token: Object to check for cancellation.
            download_item: Optional dictionary containing item details (for compatibility).
            output_path: Optional output path override (for compatibility).

        Returns:
            Dict containing metadata of downloaded file.

        Raises:
            Exception: If download fails or is cancelled.
        """
        # pylint: disable=unused-argument
        options = self.options.copy()

        # Handle path override
        if output_path and "outtmpl" in options:
            try:
                current = options.get("outtmpl")
                template_name = (
                    Path(str(current)).name if current else "%(title)s.%(ext)s"
                )
                options["outtmpl"] = str(Path(output_path) / template_name)
                logger.debug("yt-dlp outtmpl overridden to %s", options["outtmpl"])
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Failed to apply output path override: %s", exc)

        # Add progress hooks
        hooks = options.setdefault("progress_hooks", [])

        # 1. Cancellation Hook
        def check_cancel(d):
            if cancel_token:
                # Support both method check() and attribute cancelled
                if hasattr(cancel_token, "is_set") and cancel_token.is_set():
                    # pylint: disable=broad-exception-raised
                    raise InterruptedError("Download Cancelled by user")
                if hasattr(cancel_token, "cancelled") and cancel_token.cancelled:
                    # pylint: disable=broad-exception-raised
                    raise InterruptedError("Download Cancelled by user")

        hooks.append(check_cancel)

        # 2. Progress Hook
        if progress_hook:
            hooks.append(progress_hook)

        # 3. Logger redirection (optional, to keep stdout clean)
        # options['logger'] = logger # This might be too verbose

        try:
            logger.info("Starting yt-dlp download: %s", url)
            # mypy: options is dict[str, Any], but YoutubeDL expects _Params | None
            with yt_dlp.YoutubeDL(options) as ydl:  # type: ignore[arg-type]
                # Extract info and download
                info = ydl.extract_info(url, download=True)

                # Handle null info (can happen in some cases)
                if not info:
                    # pylint: disable=broad-exception-raised
                    raise Exception("Failed to extract video info")

                # Handle Playlists
                if "entries" in info:
                    entries_raw = info.get("entries", [])
                    # entries_raw is typed as object by mypy, but we know it is iterable if not None
                    # We cast to Iterable[Any] to satisfy mypy

                    entries_iterable = cast(Iterable[Any], entries_raw)
                    entries_list = (
                        list(entries_iterable) if entries_raw is not None else []
                    )
                    # yt-dlp inserts None for entries it could not download when
                    # ignoreerrors is enabled; surface that instead of reporting
                    # a false success count.
                    failed = sum(1 for entry in entries_list if not entry)
                    succeeded = len(entries_list) - failed
                    if failed:
                        logger.warning(
                            "Playlist %s: %d of %d entries failed",
                            url,
                            failed,
                            len(entries_list),
                        )
                    return {
                        "filename": info.get("title", "Playlist"),
                        # Omit filepath for playlists to avoid misleading template string
                        "title": info.get("title", "Playlist"),
                        "entries": succeeded,
                        "failed_entries": failed,
                        "type": "playlist",
                    }

                # Handle Single Video
                prepared_filename = ydl.prepare_filename(info)
                filename = self._existing_file_candidate(info, prepared_filename)
                try:
                    file_size = (
                        os.path.getsize(filename) if os.path.exists(filename) else None
                    )
                except OSError:
                    file_size = None

                return {
                    "filename": os.path.basename(filename),
                    "filepath": filename,
                    "title": info.get("title", "Unknown Title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "type": "video",
                    "size": file_size,
                    "file_size": file_size,
                }

        except Exception as e:
            # Detect cancellation to re-raise cleanly
            msg = str(e)
            if "Cancelled" in msg or "Interrupted" in msg:
                logger.info("Download cancelled via hook.")
                # pylint: disable=broad-exception-raised
                raise InterruptedError("Download Cancelled by user") from e

            logger.error("yt-dlp error for %s: %s", url, e)
            raise
