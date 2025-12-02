import logging
import os
import re
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        return filename

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

        # Configure session with retries for initial connection
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        # Initial HEAD request to resolve redirects and get filename/size
        try:
            with session.head(url, allow_redirects=True, timeout=10) as h:
                h.raise_for_status()
                final_url = h.url
                total_size = int(h.headers.get("content-length", 0))

                if not filename:
                    filename = GenericDownloader._get_filename_from_headers(url, h.headers)
        except Exception:
            # Fallback if HEAD fails (some servers block HEAD)
            final_url = url
            total_size = 0
            if not filename:
                filename = os.path.basename(url.split("?")[0]) or "downloaded_file"

        final_path = os.path.join(output_path, filename)

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
                return {
                    "filename": filename,
                    "filepath": final_path,
                    "url": url,
                    "size": total_size
                }

        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                # Check cancellation before request
                if cancel_token:
                    if hasattr(cancel_token, 'is_set') and cancel_token.is_set():
                        raise InterruptedError("Download Cancelled by user")
                    if hasattr(cancel_token, 'cancelled') and cancel_token.cancelled:
                        raise InterruptedError("Download Cancelled by user")

                logger.debug("Attempting download (try %d/%d) for %s", retry_count + 1, max_retries, url)

                with session.get(final_url, stream=True, headers=headers, timeout=REQUEST_TIMEOUT) as r:
                    r.raise_for_status()

                    # Update total size if not known or changed (e.g. server ignored Range)
                    if r.status_code == 206:
                         # Partial content
                         pass
                    elif r.status_code == 200:
                         # Server ignored range, resetting
                         if downloaded > 0:
                             logger.warning("Server does not support resume. Restarting.")
                             downloaded = 0
                             mode = "wb"
                         total_size = int(r.headers.get("content-length", 0))

                    start_time = time.time()
                    last_update_time = 0.0

                    with open(final_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                            if cancel_token:
                                if hasattr(cancel_token, 'is_set') and cancel_token.is_set():
                                    raise InterruptedError("Download Cancelled by user")
                                if hasattr(cancel_token, 'cancelled') and cancel_token.cancelled:
                                    raise InterruptedError("Download Cancelled by user")

                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                current_time = time.time()
                                if current_time - last_update_time > 0.2:  # Update every 200ms
                                    elapsed = current_time - start_time
                                    speed = (downloaded - (0 if mode=="wb" else 0)) / elapsed if elapsed > 0 else 0 # Speed calculation is rough here
                                    # Actually speed should be bytes downloaded in this session / time
                                    # But let's keep it simple

                                    if progress_hook:
                                        percent_str = f"{(downloaded / total_size) * 100:.1f}%" if total_size > 0 else "N/A"
                                        progress_hook({
                                            "status": "downloading",
                                            "_percent_str": percent_str,
                                            "_speed_str": "Calculating...", # improving speed calc requires improved state
                                            "_eta_str": "Calculating...",
                                            "_total_bytes_str": f"{total_size / 1024 / 1024:.1f} MiB" if total_size else "N/A",
                                            "filename": filename,
                                        })
                                    last_update_time = current_time

                    if progress_hook:
                        progress_hook({
                            "status": "finished",
                            "filename": filename,
                            "filepath": final_path,
                        })

                    return {
                        "filename": filename,
                        "filepath": final_path,
                        "url": url,
                        "size": downloaded
                    }

            except InterruptedError:
                logger.info("Download cancelled by user.")
                raise # Propagate up

            except (requests.exceptions.RequestException, IOError) as e:
                last_error = e
                retry_count += 1
                logger.warning("Download error: %s. Retrying...", e)
                time.sleep(2 ** retry_count)

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
    filename: Optional[str],
    progress_hook: Callable,
    cancel_token: Optional[Any] = None,
    max_retries: int = 3,
):
    """
    Legacy wrapper for GenericDownloader.download.
    """
    return GenericDownloader.download(
        url, output_path, progress_hook, cancel_token, max_retries, filename
    )
