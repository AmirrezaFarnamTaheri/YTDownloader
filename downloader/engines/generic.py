"""
Generic downloader engine using requests.
Supports resumable downloads, retry with exponential backoff, and robust filename extraction.
"""

import logging
import os
import re
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ui_utils import validate_url

logger = logging.getLogger(__name__)

# Constants to avoid magic numbers and make tuning easier
CHUNK_SIZE_BYTES = 64 * 1024  # 64KB chunks for better throughput
REQUEST_TIMEOUT = (15, 60)  # (connect timeout, read timeout)


class GenericDownloader:
    """
    Generic downloader engine using requests.
    Supports resumable downloads, retry with exponential backoff, and robust filename extraction.
    """

    @staticmethod
    def _get_filename_from_headers(url: str, headers: Dict[str, Any]) -> str:
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
        # Remove null bytes, directory separators, and control chars
        filename = os.path.basename(filename)
        # More robust sanitization: remove known invalid characters on Windows/Unix
        invalid_chars = r'<>:"/\\|?*' + "".join(map(chr, range(32)))
        filename = "".join(c for c in filename if c not in invalid_chars).strip()

        # Neutralize dot-only or traversal-like names
        if filename in {".", ".."}:
            filename = "downloaded_file"
        # Collapse leading/trailing dots and spaces which are problematic on Windows
        filename = filename.strip(" .")
        # Replace remaining occurrences of '..' to avoid traversal implications
        while ".." in filename:
            filename = filename.replace("..", "-")

        # Avoid Windows reserved device names (case-insensitive), with or without extension
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        name_root = filename.split(".")[0].upper() if filename else ""
        if name_root in reserved:
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
            raise InterruptedError("Download Cancelled by user")
        if hasattr(token, "cancelled") and token.cancelled:
            raise InterruptedError("Download Cancelled by user")

        # Check for explicit check() method (used in tests)
        if hasattr(token, "check"):
            try:
                token.check()
            except Exception as e:
                # If check raises exception, we propagate it or wrap it
                if "Cancel" in str(e):
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
                raise ValueError(f"Invalid output path: {e}")

        # Initial HEAD request to resolve redirects and get filename/size
        try:
            GenericDownloader._check_cancel(cancel_token)

            # Use requests.head directly
            h = requests.head(url, allow_redirects=True, timeout=10)
            h.raise_for_status()
            final_url = h.url
            total_size = int(h.headers.get("content-length", 0))

            if not filename:
                filename = GenericDownloader._get_filename_from_headers(url, h.headers)
        except InterruptedError:
            raise
        except Exception:
            # Fallback if HEAD fails (some servers block HEAD)
            final_url = url
            total_size = 0
            if not filename:
                filename = os.path.basename(url.split("?")[0]) or "downloaded_file"

        # Sanitize filename again just in case (e.g. if filename came from arg)
        filename = os.path.basename(filename)
        # Robust sanitization
        invalid_chars = r'<>:"/\\|?*' + "".join(map(chr, range(32)))
        filename = "".join(c for c in filename if c not in invalid_chars)

        final_path = os.path.join(output_path, filename)

        # Ensure final path is inside output path (Path Traversal check)
        if not os.path.commonpath([final_path, output_path]) == output_path:
            # Should be covered by basename, but extra safety
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
                    last_update_time = 0.0

                    with open(final_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                            GenericDownloader._check_cancel(cancel_token)

                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                current_time = time.time()
                                if (
                                    current_time - last_update_time > 0.2
                                ):  # Update every 200ms
                                    elapsed = max(current_time - start_time, 1e-6)
                                    # Speed calc logic would go here if needed

                                    if progress_hook:
                                        percent_str = (
                                            f"{(downloaded / total_size) * 100:.1f}%"
                                            if total_size > 0
                                            else "N/A"
                                        )
                                        progress_hook(
                                            {
                                                "status": "downloading",
                                                "_percent_str": percent_str,
                                                "_speed_str": "Calculating...",
                                                "_eta_str": "Calculating...",
                                                "_total_bytes_str": (
                                                    f"{total_size / 1024 / 1024:.1f} MiB"
                                                    if total_size
                                                    else "N/A"
                                                ),
                                                "filename": filename,
                                            }
                                        )
                                    last_update_time = current_time

                                    # Periodic flush to disk for data integrity
                                    try:
                                        f.flush()
                                        os.fsync(f.fileno())
                                    except Exception:
                                        pass

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
