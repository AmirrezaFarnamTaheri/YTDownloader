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

Attempts to claim and submit as many queued items as available concurrency allows,
respecting throttling and max concurrency.

### `tasks.fetch_info_task(url: str, view_card: Any, page: Any) -> None`

Background metadata fetch operation with UI callback dispatch.

### `tasks.configure_concurrency(max_workers: int) -> bool`

Swaps the submission semaphore that gates download concurrency. The worker pool
is a single long-lived `ThreadPoolExecutor`, so this call never shuts down or
orphans in-flight downloads. Returns `False` for non-positive values.

## State and UI APIs

### `theme.Theme.apply_theme_mode(mode: str) -> None`

Switches the active palette (`dark`, `light`, `high_contrast`). Re-binds both
the `Theme.*` class attributes and the legacy nested proxies.

### `ui_manager.UIManager.refresh_theme() -> None`

Rebuilds the view tree with the current palette and re-mounts it on the page.
Required after a runtime theme change because Flet controls capture colours at
construction time.

### `queue_manager.QueueManager.update_item_status(item_id, status, updates=None) -> None`

O(1) status/progress update backed by an internal id index. Safe to call from
worker threads at high frequency.

### `localization_manager.LocalizationManager.get(key, *args, default=None) -> str`

Returns the localized string for `key`. Extra positional arguments are format
arguments (`LM.get("stats_queued", 3)`); when the key is missing everywhere the
`default` keyword is returned, otherwise the key itself is surfaced so missing
translations stay visible. Positional strings are *not* defaults — they are
interpolated into the template, and `tests/test_locale_key_usage.py` rejects
call sites that try it.

### `app_paths.data_dir() -> Path` / `app_paths.data_file(name) -> Path`

Resolve the per-user data directory (`~/.streamcatch` by default). Set
`STREAMCATCH_DATA_DIR` to relocate it — this is what the test suite uses to run
against a temporary folder instead of the developer's real configuration,
history, and log. `ConfigManager.CONFIG_FILE`, `HistoryManager.DB_FILE`, and the
logger resolve their path once at import, so set the variable before the
application (or the test session) starts.

### `ui_utils.safe_update(control: ft.Control) -> bool`

Pushes a control to the client only when it is mounted (`control.page` is set)
and returns whether an update was issued. Views are refreshed from background
timers while the user may have navigated elsewhere, so every repaint that can
race with navigation must go through this helper instead of `control.update()`,
which raises `AssertionError: Control must be added to the page first` for
detached controls.

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
- `get_stats() -> dict` — `{"total_downloads": int, "total_size_mb": float}`;
  understands both raw byte counts and pre-formatted sizes such as `"12.50 MB"`
- `export_to_json(filepath: str) -> None`
- `export_to_csv(filepath: str) -> None`
- `import_entries(entries: Any) -> tuple[int, int]` — returns
  `(imported, skipped)`; entries already present (matched by `url` +
  `timestamp`) are skipped so re-importing a backup never duplicates history
- `import_from_json_file(filepath: str) -> tuple[int, int]` — reads a file
  written by `export_to_json`, enforces a 5 MB cap before reading, and raises
  `ValueError` with an actionable message for missing, oversized, or non-JSON
  files. `add_entry` accepts an optional `timestamp` so imported rows keep
  their original download time.

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
