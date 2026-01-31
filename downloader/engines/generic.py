# pylint: disable=line-too-long,too-many-locals,too-many-branches,too-many-statements,too-many-arguments,broad-exception-caught,too-many-positional-arguments
"""
Generic downloader engine using requests.
Supports resumable downloads, retry with exponential backoff, and robust filename extraction.
"""

import logging
import os
import random
import re
import time
import urllib.parse
from collections.abc import Callable, Mapping
from typing import Any

import requests

from downloader.types import DownloadResult
from downloader.utils.constants import RESERVED_FILENAMES
from ui_utils import format_file_size, validate_url

logger = logging.getLogger(__name__)

# Constants to avoid magic numbers and make tuning easier
CHUNK_SIZE_BYTES = 64 * 1024  # 64KB chunks for better throughput
REQUEST_TIMEOUT = (15, 60)  # (connect timeout, read timeout)

# Global session for connection reuse
_SESSION = requests.Session()

# Rotating User-Agents
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class GenericDownloader:
    """
    Generic downloader engine using requests.
    Supports resumable downloads, retry with exponential backoff, and robust filename extraction.
    """

    # pylint: disable=too-few-public-methods

    @staticmethod
    def _get_random_ua() -> str:
        """Return a random User-Agent."""
        return random.choice(_USER_AGENTS)

    @staticmethod
    def _extract_filename_from_cd(cd_header: str) -> str | None:
        """
        Extract filename from Content-Disposition header, supporting RFC 5987.
        Prioritizes filename* (UTF-8) over filename.
        """
        if not cd_header:
            return None

        # 1. Try filename* (RFC 5987)
        # Regex to capture filename*=UTF-8''filename.ext
        # We assume UTF-8 as per standard
        match_utf8 = re.search(
            r"filename\*\s*=\s*UTF-8''([^;]+)", cd_header, re.IGNORECASE
        )
        if match_utf8:
            try:
                return urllib.parse.unquote(match_utf8.group(1))
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        # 2. Try quoted filename="foo.ext"
        match_quoted = re.search(r'filename\s*=\s*"([^"]+)"', cd_header, re.IGNORECASE)
        if match_quoted:
            return match_quoted.group(1)

        # 3. Try unquoted filename=foo.ext
        match_token = re.search(r"filename\s*=\s*([^;]+)", cd_header, re.IGNORECASE)
        if match_token:
            return match_token.group(1).strip()

        return None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to be safe for all filesystems.
        """
        if not filename:
            return "downloaded_file"

        # Strip path info
        filename = os.path.basename(filename)

        # Allow wider range of characters (Unicode) but block dangerous ones
        # Block: / \ : * ? " < > | (Windows reserved + path separators)
        # Also block control characters
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        filename = "".join(c for c in filename if ord(c) >= 32)

        # Strip leading/trailing dots and spaces
        filename = filename.strip(" .")

        # Handle reserved names on Windows
        root = filename.split(".")[0].upper()
        if root in RESERVED_FILENAMES:
            filename = f"_{filename}"

        if not filename:
            return "downloaded_file"

        return filename

    @staticmethod
    def _get_filename_from_headers(url: str, headers: Mapping[str, str]) -> str:
        """Extract filename from Content-Disposition header or fallback to URL."""
        filename = GenericDownloader._extract_filename_from_cd(
            headers.get("Content-Disposition", "")
        )

        if not filename:
            # Fallback to URL path
            path = urllib.parse.urlparse(url).path
            filename = urllib.parse.unquote(os.path.basename(path))

        return GenericDownloader._sanitize_filename(filename)

    @staticmethod
    def _check_cancel(token: Any | None):
        """Helper to check cancellation token support multiple interfaces."""
        if not token:
            return

        # Check standard threading.Event/CancelToken interfaces
        if hasattr(token, "is_set") and token.is_set():
            raise InterruptedError("Download Cancelled by user")
        if hasattr(token, "cancelled") and token.cancelled:
            raise InterruptedError("Download Cancelled by user")

        # Check for explicit check() method (used in tests)
        if hasattr(token, "check"):
            try:
                token.check()
            except Exception as e:
                if "Cancel" in str(e):
                    raise InterruptedError("Download Cancelled by user") from e
                raise

    @staticmethod
    def _prepare_headers(
        downloaded_bytes: int, total_size: int, is_resume: bool
    ) -> dict[str, str]:
        """Prepare HTTP headers for request."""
        headers = {
            "User-Agent": GenericDownloader._get_random_ua(),
        }
        if is_resume and downloaded_bytes > 0:
            headers["Range"] = f"bytes={downloaded_bytes}-"
        return headers

    @staticmethod
    def _verify_path_security(final_path: str, output_path: str) -> None:
        """Ensure final path is strictly within output path to prevent traversal."""
        final_abs = os.path.abspath(final_path)
        output_abs = os.path.abspath(output_path)
        try:
            # commonpath raises ValueError on Windows for different drives
            if os.path.commonpath([final_abs, output_abs]) != output_abs:
                raise ValueError("Path traversal detected")
        except ValueError as e:
            raise ValueError(f"Security violation: {e}") from e

    @staticmethod
    def download(
        url: str,
        output_path: str,
        progress_hook: Callable[[dict[str, Any]], None] | None = None,
        cancel_token: Any | None = None,
        max_retries: int = 3,
        filename: str | None = None,
    ) -> DownloadResult:
        """
        Downloads a file using requests with streaming.
        Supports resume and exponential backoff.
        """
        if not validate_url(url):
            raise ValueError(f"Invalid or unsafe URL: {url}")

        output_path = os.path.abspath(output_path)
        if not os.path.isdir(output_path):
            try:
                os.makedirs(output_path, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Invalid output path: {e}") from e

        # 1. HEAD Request
        try:
            GenericDownloader._check_cancel(cancel_token)
            h = _SESSION.head(url, allow_redirects=True, timeout=10)
            h.raise_for_status()
            final_url = h.url
            try:
                total_size = int(h.headers.get("content-length", 0))
            except (TypeError, ValueError):
                total_size = 0

            if not filename:
                filename = GenericDownloader._get_filename_from_headers(
                    final_url, h.headers
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("HEAD request failed: %s", exc)
            final_url = url
            total_size = 0
            if not filename:
                path = urllib.parse.urlparse(url).path
                filename = GenericDownloader._sanitize_filename(os.path.basename(path))

        # 2. Path Setup
        filename = GenericDownloader._sanitize_filename(filename or "downloaded_file")
        final_path = os.path.join(output_path, filename)
        GenericDownloader._verify_path_security(final_path, output_path)

        # 3. Resume Check
        downloaded = 0
        mode = "wb"
        if os.path.exists(final_path):
            existing = os.path.getsize(final_path)
            if total_size > 0 and existing == total_size:
                logger.info("File already downloaded: %s", final_path)
                if progress_hook:
                    progress_hook(
                        {
                            "status": "finished",
                            "filename": filename,
                            "filepath": final_path,
                        }
                    )
                return {
                    "filename": filename,
                    "filepath": final_path,
                    "url": url,
                    "title": filename,
                    "type": "video",
                    "size": total_size,
                }
            if total_size > 0 and existing < total_size:
                downloaded = existing
                mode = "ab"

        # 4. Download Loop
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                GenericDownloader._check_cancel(cancel_token)
                headers = GenericDownloader._prepare_headers(
                    downloaded, total_size, mode == "ab"
                )

                logger.debug("Starting download (try %d)", retry_count + 1)
                with _SESSION.get(
                    final_url, stream=True, headers=headers, timeout=REQUEST_TIMEOUT
                ) as r:
                    r.raise_for_status()

                    # Handle server ignoring Range
                    if r.status_code == 200 and mode == "ab":
                        logger.warning("Server ignored Range header, restarting")
                        downloaded = 0
                        mode = "wb"
                        try:
                            total_size = int(r.headers.get("content-length", 0))
                        except (ValueError, TypeError):
                            pass

                    start_time = time.time()
                    last_update_time = start_time
                    last_update_bytes = downloaded
                    speed_history: list[float] = []

                    with open(final_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                            GenericDownloader._check_cancel(cancel_token)
                            if not chunk:
                                continue

                            f.write(chunk)
                            downloaded += len(chunk)

                            # Progress Update Logic
                            curr_time = time.time()
                            if curr_time - last_update_time > 0.5:
                                diff_time = curr_time - last_update_time
                                diff_bytes = downloaded - last_update_bytes
                                speed = diff_bytes / diff_time if diff_time > 0 else 0

                                speed_history.append(speed)
                                if len(speed_history) > 10:
                                    speed_history.pop(0)
                                avg_speed = sum(speed_history) / len(speed_history)

                                if progress_hook:
                                    eta_str = "Unknown"
                                    if total_size > 0 and avg_speed > 0:
                                        rem = total_size - downloaded
                                        eta_str = f"{int(rem / avg_speed)}s"

                                    progress_hook(
                                        {
                                            "status": "downloading",
                                            "_percent_str": (
                                                f"{downloaded/total_size:.1%}"
                                                if total_size
                                                else "?"
                                            ),
                                            "_speed_str": f"{format_file_size(avg_speed)}/s",
                                            "_eta_str": eta_str,
                                            "_total_bytes_str": format_file_size(
                                                total_size
                                            ),
                                            "filename": filename,
                                            "downloaded_bytes": downloaded,
                                            "total_bytes": total_size,
                                        }
                                    )
                                last_update_time = curr_time
                                last_update_bytes = downloaded

                    if progress_hook:
                        progress_hook(
                            {
                                "status": "finished",
                                "filename": filename,
                                "filepath": final_path,
                            }
                        )

                    return {
                        "filename": filename,
                        "filepath": final_path,
                        "url": url,
                        "title": filename,
                        "type": "video",
                        "size": downloaded,
                    }

            except InterruptedError:
                raise
            except (OSError, requests.RequestException) as e:
                last_error = e
                retry_count += 1
                logger.warning("Download error: %s. Retry in %ds", e, 2**retry_count)
                time.sleep(2**retry_count)

                # Prepare for next attempt
                if os.path.exists(final_path):
                    downloaded = os.path.getsize(final_path)
                    mode = "ab"

        if last_error:
            raise last_error
        return {}


# Legacy wrapper
def download_generic(
    url: str,
    output_path: str,
    filename: str | None = None,
    progress_hook: Callable | None = None,
    cancel_token: Any | None = None,
    max_retries: int = 3,
) -> Any:
    """Legacy wrapper for GenericDownloader.download."""
    return GenericDownloader.download(
        url, output_path, progress_hook, cancel_token, max_retries, filename
    )
