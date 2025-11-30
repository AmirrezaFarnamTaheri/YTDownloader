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


def download_generic(
    url: str,
    output_path: str,
    filename: str,
    progress_hook: Callable,
    download_item: Dict[str, Any],
    cancel_token: Optional["Any"] = None,
    max_retries: int = 3,
):
    """
    Downloads a file using requests with streaming.
    Supports resumable downloads and retry with exponential backoff.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

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
            logger.debug(f"Request headers: {headers}")
            # Start stream with timeout suitable for large files
            with requests.get(
                url, stream=True, headers=headers, timeout=REQUEST_TIMEOUT
            ) as r:
                logger.debug(f"Response status: {r.status_code}, headers: {r.headers}")
                r.raise_for_status()

                # Handle resume response
                if r.status_code == 206:
                    # Partial content response (resume successful)
                    content_range = r.headers.get("Content-Range", "")
                    logger.info(f"Resume accepted: {content_range}")
                    total_size = downloaded + int(r.headers.get("content-length", 0))
                elif r.status_code == 200:
                    # Full content (either new download or server doesn't support resume)
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
                        if cancel_token:
                            cancel_token.check()

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            current_time = time.time()
                            # Update UI every 0.1s or so to avoid flooding
                            if current_time - last_update_time > 0.1:
                                elapsed = current_time - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                eta = (
                                    (total_size - downloaded) / speed
                                    if speed > 0 and total_size > 0
                                    else 0
                                )

                                progress_hook(
                                    {
                                        "status": "downloading",
                                        "downloaded_bytes": downloaded,
                                        "total_bytes": total_size,
                                        "speed": speed,
                                        "eta": eta,
                                        "filename": filename,
                                    },
                                    download_item,
                                )
                                last_update_time = current_time

                progress_hook(
                    {
                        "status": "finished",
                        "filename": final_path,
                        "total_bytes": total_size,
                    },
                    download_item,
                )

                # Success - break retry loop
                logger.info(f"Generic download finished: {final_path}")
                return

        except (requests.exceptions.RequestException, IOError) as e:
            last_error = e
            retry_count += 1
            if retry_count <= max_retries:
                wait_time = 2**retry_count  # Exponential backoff: 2, 4, 8 seconds
                logger.warning(
                    f"Download failed (attempt {retry_count}/{max_retries}): {e}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
                # Update headers for resume on retry
                if os.path.exists(final_path):
                    downloaded = os.path.getsize(final_path)
                    headers["Range"] = f"bytes={downloaded}-"
        except Exception as e:
            # Non-retryable errors (like cancellation)
            logger.error(f"Generic download error: {e}", exc_info=True)
            raise

    # If we exhausted retries
    if last_error:
        logger.error(f"Generic download failed after {max_retries} retries.")
        raise last_error
