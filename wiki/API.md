# API Reference

## Downloader Package

### `downloader.core.download_video(options: DownloadOptions) -> Dict`
The main entry point for downloading.
*   **options**: A `DownloadOptions` dataclass containing all parameters.
*   **Returns**: A dictionary with download results (filepath, etc.).

### `downloader.info.get_video_info(url: str, cookies: str = None) -> Dict`
Fetches metadata for a given URL.

## Managers

### `QueueManager`
*   `add_item(item)`: Adds a new item to the queue.
*   `claim_next_downloadable()`: Returns the next pending item and marks it as processing.
*   `update_item_status(id, status, ...)`: Updates the status of an item.

### `HistoryManager`
*   `add_entry(...)`: detailed logging of completed downloads.
*   `get_history(limit, offset)`: Retrieves paginated history.
