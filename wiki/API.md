# Internal API Reference

This document summarizes the primary callable surfaces used across the project.

## Entry Points

### `main.main(page: ft.Page) -> None`

Application startup callback used by Flet.

- Loads localization and theme.
- Creates `UIManager` and `AppController`.
- Registers lifecycle cleanup hooks.

### `downloader.core.download_video(options: DownloadOptions) -> dict[str, Any]`

Primary download execution API.

- Validates options and output paths.
- Chooses Telegram/generic/yt-dlp engine path.
- Returns download metadata (`filepath`, `filename`, etc.).

### `downloader.info.get_video_info(url, cookies_from_browser=None, cookies_from_browser_profile=None) -> dict | None`

Fetches metadata without downloading media.

## Orchestration APIs

### `tasks.process_queue(page: ft.Page | None) -> None`

Attempts to claim and submit a queue item to the executor respecting throttling and max concurrency.

### `tasks.fetch_info_task(url: str, view_card: Any, page: Any) -> None`

Background metadata fetch operation with UI callback dispatch.

### `tasks.configure_concurrency(max_workers: int) -> bool`

Reconfigures submission semaphore + executor lifecycle.

## Queue APIs (`QueueManager`)

### Mutation

- `add_item(item: dict[str, Any]) -> None`
- `update_item_status(item_id: str, status: str, updates: dict | None = None) -> None`
- `remove_item(item: dict[str, Any]) -> None`
- `swap_items(index1: int, index2: int) -> None`
- `retry_item(item_id: str | None) -> bool`

### Control

- `cancel_item(item_id: str) -> None`
- `cancel_all() -> int`
- `pause_all() -> int`
- `resume_all() -> int`
- `clear_completed() -> int`

### Selection and Metrics

- `claim_next_downloadable() -> QueueItem | None`
- `update_scheduled_items(now: datetime) -> int`
- `get_all() -> list[QueueItem]`
- `get_statistics() -> dict[str, int]`

## History APIs (`HistoryManager`)

- `add_entry(entry: dict[str, Any]) -> None`
- `get_history(limit=50, offset=0, search_query="") -> list[dict]`
- `delete_entry(entry_id: int) -> bool`
- `delete_entries(entry_ids: list[int]) -> bool`
- `search_history(query: str, search_in: list[str] | None = None) -> dict`
- `get_download_activity(days=7) -> list[dict]`
- `export_to_json(filepath: str) -> None`
- `export_to_csv(filepath: str) -> None`

## Sync and Cloud APIs

### `SyncManager`

- `sync_up() -> None`
- `sync_down() -> None`
- `export_data(export_path: str) -> None`
- `import_data(import_path: str) -> None`
- `start_auto_sync() -> None`
- `stop_auto_sync() -> None`

### `CloudManager`

- `upload_file(file_path: str, provider="google_drive") -> None`
- `download_file(filename: str, destination_path: str, provider="google_drive") -> bool`

## Build Tool APIs

### `scripts/build_installer.py`

Builds native desktop artifacts using Nuitka and optionally Inno Setup on Windows.

### `scripts/build_mobile.py`

Builds mobile target (`apk`/`aab`/`ipa`) and validates artifact creation.
