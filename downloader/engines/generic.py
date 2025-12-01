import logging
import os
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import requests

if TYPE_CHECKING:
    from utils import CancelToken

logger = logging.getLogger(__name__)

# Constants to avoid magic numbers and make tuning easier
CHUNK_SIZE_BYTES = 32 * 1024  # 32KB chunks
REQUEST_TIMEOUT = (15, 300)  # (connect timeout, read timeout) in seconds


class GenericDownloader:
    """
    Generic downloader engine using requests.
    Supports resumable downloads and retry with exponential backoff.
    """

    @staticmethod
    def download(
        url: str,
        output_path: str,
        progress_hook: Optional[Callable] = None,
        cancel_token: Optional[Any] = None,
        max_retries: int = 3,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Downloads a file using requests with streaming.

        Args:
            url: URL to download
            output_path: Directory to save to
            progress_hook: Callback for progress
            cancel_token: Token to check for cancellation
            max_retries: Number of retries
            filename: Optional filename override

        Returns:
            Dict with metadata (filename, filepath, etc.)
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        if not filename:
            # Determine filename from URL or headers (pre-check)
            try:
                with requests.head(url, allow_redirects=True, timeout=10) as h:
                    if "Content-Disposition" in h.headers:
                        import re
                        fname = re.findall("filename=(.+)", h.headers["Content-Disposition"])
                        if fname:
                            filename = fname[0].strip('"')
                        else:
                            filename = url.split("/")[-1].split("?")[0]
                    else:
                        filename = url.split("/")[-1].split("?")[0]
            except Exception:
                filename = url.split("/")[-1].split("?")[0]

            if not filename:
                filename = "downloaded_file"

        # Ensure filename is just a name, not a path
        filename = os.path.basename(filename)
        final_path = os.path.join(output_path, filename)
        downloaded = 0

        # Check if partial file exists (for resume support)
        if os.path.exists(final_path):
            downloaded = os.path.getsize(final_path)
            logger.info(f"Resuming download from byte {downloaded}")
            headers["Range"] = f"bytes={downloaded}-"

        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                logger.debug(f"Attempting download (try {retry_count + 1}) for {url}")
                # Start stream with timeout suitable for large files
                with requests.get(
                    url, stream=True, headers=headers, timeout=REQUEST_TIMEOUT
                ) as r:
                    r.raise_for_status()

                    # Handle resume response
                    if r.status_code == 206:
                        # Partial content response (resume successful)
                        total_size = downloaded + int(r.headers.get("content-length", 0))
                    elif r.status_code == 200:
                        # Full content
                        total_size = int(r.headers.get("content-length", 0))
                        if downloaded > 0:
                            logger.warning(
                                "Server doesn't support resume, starting from beginning"
                            )
                            downloaded = 0
                    else:
                        total_size = int(r.headers.get("content-length", 0))

                    start_time = time.time()
                    last_update_time = start_time

                    # Open file in append mode if resuming, otherwise write mode
                    mode = "ab" if r.status_code == 206 else "wb"
                    with open(final_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                            if cancel_token and hasattr(cancel_token, 'check'):
                                cancel_token.check()
                            elif cancel_token and getattr(cancel_token, 'cancelled', False):
                                raise Exception("Cancelled")

                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                current_time = time.time()
                                # Update UI every 0.1s
                                if progress_hook and (current_time - last_update_time > 0.1):
                                    elapsed = current_time - start_time
                                    speed = downloaded / elapsed if elapsed > 0 else 0
                                    eta = (
                                        (total_size - downloaded) / speed
                                        if speed > 0 and total_size > 0
                                        else 0
                                    )

                                    # Mimic yt-dlp hook format
                                    progress_hook({
                                        "status": "downloading",
                                        "_percent_str": f"{(downloaded/total_size)*100:.1f}%" if total_size else "N/A",
                                        "_speed_str": f"{speed/1024/1024:.1f} MiB/s",
                                        "_eta_str": f"{int(eta)}s",
                                        "_total_bytes_str": f"{total_size/1024/1024:.1f} MiB",
                                        "filename": filename,
                                    })
                                    last_update_time = current_time

                    if progress_hook:
                        progress_hook({
                            "status": "finished",
                            "filename": final_path,
                            "filepath": final_path,
                        })

                    # Success - break retry loop
                    logger.info(f"Generic download finished: {final_path}")
                    return {
                        "filename": filename,
                        "filepath": final_path,
                        "url": url
                    }

            except (requests.exceptions.RequestException, IOError) as e:
                last_error = e
                retry_count += 1
                if retry_count <= max_retries:
                    wait_time = 2**retry_count
                    logger.warning(
                        f"Download failed (attempt {retry_count}/{max_retries}): {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    if os.path.exists(final_path):
                        downloaded = os.path.getsize(final_path)
                        headers["Range"] = f"bytes={downloaded}-"
            except Exception as e:
                logger.error(f"Generic download error: {e}", exc_info=True)
                raise

        # If we exhausted retries
        if last_error:
            logger.error(f"Generic download failed after {max_retries} retries.")
            raise last_error
        return {}


# Legacy wrapper for compatibility
def download_generic(
    url: str,
    output_path: str,
    filename: str,  # This argument is ignored by GenericDownloader.download as it detects filename
    progress_hook: Callable,
    download_item: Dict[str, Any],
    cancel_token: Optional[Any] = None,
    max_retries: int = 3,
):
    """
    Legacy wrapper for GenericDownloader.download.
    """
    # Create a progress hook wrapper if needed to match old dict format
    # The new download() calls hook with {_percent_str...}, old might expect diff?
    # Actually the new one mimics yt-dlp which is what core expects.
    # The old `download_generic` called hook with download_item as 2nd arg.
    # New `GenericDownloader.download` calls hook with just 1 arg (d).

    def hook_wrapper(d):
        progress_hook(d, download_item)

    return GenericDownloader.download(
        url, output_path, hook_wrapper, cancel_token, max_retries, filename
    )
