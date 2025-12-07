# pylint: disable=line-too-long,too-many-locals,too-many-branches,too-many-statements,too-many-arguments,broad-exception-caught,too-many-positional-arguments
"""
Generic downloader engine using requests.
Supports resumable downloads, retry with exponential backoff, and robust filename extraction.
"""

import logging
import os
import re
import time
from typing import Any, Callable, Dict, Mapping, Optional

import requests

from downloader.utils.constants import RESERVED_FILENAMES
from ui_utils import format_file_size, validate_url

logger = logging.getLogger(__name__)

# Constants to avoid magic numbers and make tuning easier
CHUNK_SIZE_BYTES = 64 * 1024  # 64KB chunks for better throughput
REQUEST_TIMEOUT = (15, 60)  # (connect timeout, read timeout)


class GenericDownloader:
    """
    Generic downloader engine using requests.
    Supports resumable downloads, retry with exponential backoff, and robust filename extraction.
    """

    # pylint: disable=too-few-public-methods

    @staticmethod
    def _get_filename_from_headers(url: str, headers: Mapping[str, str]) -> str:
        """Extract filename from Content-Disposition header or fallback to URL."""
        filename = ""
        cd = headers.get("Content-Disposition")
        if cd:
            # Try to extract filename="name" or filename*=UTF-8''name
            # Simplified regex for demonstration
            fnames = re.findall(r'filename\*?=(?:[a-zA-Z0-9-]+\'\')?"?([^";]+)"?', cd)
            if fnames:
                filename = fnames[0]

        if not filename:
            # Fallback to URL path
            path = url.split("?")[0]
            filename = os.path.basename(path)

        if not filename:
            filename = "downloaded_file"

        # Sanitize filename (Path Traversal Protection + General Safety)
        # Step 1: Strip any directory components and path separators
        # This handles: ../../../etc/passwd, C:\path\file, /etc/passwd
        filename = os.path.basename(filename)

        # Step 2: Stricter allowlist approach (A-Z, a-z, 0-9, -, _, .)
        # This removes: colons (C:), null bytes, control chars, unicode, etc.
        # Allowlist is more secure than blocklist for cross-platform safety
        filename = re.sub(r"[^A-Za-z0-9\-\_\.]", "", filename).strip()

        # Neutralize dot-only or traversal-like names
        if filename in {".", ".."}:
            filename = "downloaded_file"
        # Collapse leading/trailing dots and spaces which are problematic on Windows
        filename = filename.strip(" .")
        # Replace remaining occurrences of '..' to avoid traversal implications
        while ".." in filename:
            filename = filename.replace("..", "-")

        # Avoid Windows reserved device names (case-insensitive), with or without extension
        name_root = filename.split(".")[0].upper() if filename else ""
        if name_root in RESERVED_FILENAMES:
            filename = f"_{filename}" if filename else "downloaded_file"

        if not filename:
            filename = "downloaded_file"

        return filename

    @staticmethod
    def _check_cancel(token: Optional[Any]):
        """Helper to check cancellation token support multiple interfaces."""
        if not token:
            return

        # Check standard threading.Event/CancelToken interfaces
        if hasattr(token, "is_set") and token.is_set():
            # pylint: disable=broad-exception-raised
            raise InterruptedError("Download Cancelled by user")
        if hasattr(token, "cancelled") and token.cancelled:
            # pylint: disable=broad-exception-raised
            raise InterruptedError("Download Cancelled by user")

        # Check for explicit check() method (used in tests)
        if hasattr(token, "check"):
            try:
                token.check()
            except Exception as e:
                # If check raises exception, we propagate it or wrap it
                if "Cancel" in str(e):
                    # pylint: disable=broad-exception-raised
                    raise InterruptedError("Download Cancelled by user") from e
                raise

    @staticmethod
    def download(
        url: str,
        output_path: str,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
        max_retries: int = 3,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Downloads a file using requests with streaming.

        Args:
            url: URL to download.
            output_path: Directory to save to.
            progress_hook: Callback for progress.
            cancel_token: Token to check for cancellation.
            max_retries: Number of retries.
            filename: Optional filename override.

        Returns:
            Dict with metadata (filename, filepath, etc.).
        """
        # SSRF Protection: Validate URL scheme and format
        if not validate_url(url):
            raise ValueError(f"Invalid or unsafe URL: {url}")

        # Path Traversal Protection: Validate output_path
        output_path = os.path.abspath(output_path)
        if not os.path.isdir(output_path):
            # Try to create? The core logic usually handles this,
            # but here we should ensure we are writing to a valid place.
            try:
                os.makedirs(output_path, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Invalid output path: {e}") from e

        # Initial HEAD request to resolve redirects and get filename/size
        try:
            GenericDownloader._check_cancel(cancel_token)

            # Use requests.head directly
            h = requests.head(url, allow_redirects=True, timeout=10)
            h.raise_for_status()
            final_url = h.url
            cl_header = h.headers.get("content-length")
            try:
                total_size = int(cl_header) if cl_header is not None else 0
            except (TypeError, ValueError):
                total_size = 0

            if not filename:
                filename = GenericDownloader._get_filename_from_headers(url, h.headers)
        except InterruptedError:
            raise
        except Exception:  # pylint: disable=broad-exception-caught
            # Fallback if HEAD fails (some servers block HEAD)
            final_url = url
            total_size = 0
            if not filename:
                filename = os.path.basename(url.split("?")[0]) or "downloaded_file"

        # Sanitize filename again just in case (e.g. if filename came from arg)
        filename = os.path.basename(filename)
        # Stricter allowlist approach
        filename = re.sub(r"[^A-Za-z0-9\-\_\.]", "", filename).strip()

        final_path = os.path.join(output_path, filename)

        # Ensure final path is inside output path (Path Traversal check)
        final_dir = os.path.dirname(os.path.abspath(final_path))
        base_dir = os.path.abspath(output_path)
        if os.path.commonpath([final_dir, base_dir]) != base_dir:
            raise ValueError("Detected path traversal attempt in filename")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        downloaded = 0
        mode = "wb"

        # Resume support logic
        if os.path.exists(final_path):
            existing_size = os.path.getsize(final_path)
            if total_size > 0 and existing_size < total_size:
                logger.info("Resuming download from byte %d", existing_size)
                downloaded = existing_size
                headers["Range"] = f"bytes={downloaded}-"
                mode = "ab"
            elif total_size > 0 and existing_size == total_size:
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
                    "size": total_size,
                }

        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                GenericDownloader._check_cancel(cancel_token)

                logger.debug(
                    "Attempting download (try %d/%d) for %s",
                    retry_count + 1,
                    max_retries,
                    url,
                )

                with requests.get(
                    final_url, stream=True, headers=headers, timeout=REQUEST_TIMEOUT
                ) as r:
                    r.raise_for_status()

                    # Update total size if not known or changed (e.g. server ignored Range)
                    if r.status_code == 206:
                        # Partial content
                        pass
                    elif r.status_code == 200:
                        # Server ignored range, resetting
                        if downloaded > 0:
                            logger.warning(
                                "Server does not support resume. Restarting."
                            )
                            downloaded = 0
                            mode = "wb"
                        total_size = int(r.headers.get("content-length", 0))

                    start_time = time.time()
                    last_update_time = start_time
                    last_update_bytes = downloaded

                    # For moving average speed
                    speed_history = []

                    with open(final_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                            GenericDownloader._check_cancel(cancel_token)

                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                current_time = time.time()
                                time_diff = current_time - last_update_time

                                if time_diff > 0.5:  # Update every 500ms
                                    bytes_diff = downloaded - last_update_bytes
                                    speed = (
                                        bytes_diff / time_diff if time_diff > 0 else 0
                                    )

                                    # Simple moving average for stability
                                    speed_history.append(speed)
                                    if len(speed_history) > 5:
                                        speed_history.pop(0)
                                    avg_speed = sum(speed_history) / len(speed_history)

                                    eta_str = "Unknown"
                                    if total_size > 0 and avg_speed > 0:
                                        remaining = total_size - downloaded
                                        seconds = remaining / avg_speed
                                        if seconds < 60:
                                            eta_str = f"{int(seconds)}s"
                                        elif seconds < 3600:
                                            eta_str = f"{int(seconds//60)}m {int(seconds%60)}s"
                                        else:
                                            eta_str = f"{int(seconds//3600)}h {int((seconds%3600)//60)}m"

                                    if progress_hook:
                                        percent_str = (
                                            f"{(downloaded / total_size) * 100:.1f}%"
                                            if total_size > 0
                                            else "N/A"
                                        )
                                        speed_str = f"{format_file_size(avg_speed)}/s"

                                        progress_hook(
                                            {
                                                "status": "downloading",
                                                "_percent_str": percent_str,
                                                "_speed_str": speed_str,
                                                "_eta_str": eta_str,
                                                "_total_bytes_str": (
                                                    format_file_size(total_size)
                                                ),
                                                "filename": filename,
                                                "downloaded_bytes": downloaded,
                                                "total_bytes": total_size,
                                            }
                                        )

                                    last_update_time = current_time
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
                        "size": downloaded,
                    }

            except InterruptedError:
                logger.info("Download cancelled by user.")
                raise  # Propagate up

            except (requests.exceptions.RequestException, IOError) as e:
                last_error = e
                retry_count += 1
                logger.warning("Download error: %s. Retrying...", e)

                if retry_count > max_retries:
                    break

                time.sleep(2**retry_count)  # Backoff

                # Prepare for retry (resume if possible)
                if os.path.exists(final_path):
                    downloaded = os.path.getsize(final_path)
                    headers["Range"] = f"bytes={downloaded}-"
                    mode = "ab"

        if last_error:
            logger.error("Download failed after retries: %s", last_error)
            raise last_error

        return {}


# Legacy wrapper for compatibility (removed download_item)
def download_generic(
    url: str,
    output_path: str,
    filename: Optional[str] = None,  # Make optional to match usage
    progress_hook: Optional[Callable] = None,
    cancel_token: Optional[Any] = None,
    max_retries: int = 3,
):
    """
    Legacy wrapper for GenericDownloader.download.
    """
    return GenericDownloader.download(
        url, output_path, progress_hook, cancel_token, max_retries, filename
    )
