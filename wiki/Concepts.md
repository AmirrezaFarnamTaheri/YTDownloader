# Core Concepts

## Download Sources and Engines

### Extractors

Extractors determine metadata and media endpoints.

- `downloader.info`: metadata via `yt-dlp` + fallback extraction.
- `TelegramExtractor`: public Telegram page parsing for media URLs.
- `GenericExtractor`: lightweight HEAD-based fallback metadata.

### Download Engines

Engines perform the actual binary transfer.

- `YTDLPWrapper`: full-featured site extraction/download flow.
- `GenericDownloader`: direct file transfer with retries and resume behavior.

## Queue as Source of Truth

`QueueManager` is the authoritative runtime state for download items.

- All status transitions happen centrally.
- Worker synchronization relies on condition notifications.
- UI components render based on queue snapshots, not ad-hoc worker state.

## Concurrency and Backpressure

- Executor max workers are configurable (`max_concurrent_downloads`).
- Submission semaphore throttles queue job dispatch.
- Active count prevents over-allocation when queue grows quickly.

## Cancellation Contract

Cancellation is cooperative.

- `CancelToken` instances are registered per item.
- Worker hooks and download engines check cancellation regularly.
- `QueueManager.cancel_item()` updates state and signals workers.

## Metadata and History

- Metadata retrieval is pre-download and optional.
- Successful/failed outcomes are persisted via `HistoryManager`.
- Activity charts derive from historical aggregate data.

## Sync Model

- Data export/import bundles config + history.
- Path traversal protections are enforced during import.
- Cloud sync is best-effort, lock-protected, and retry-safe at manager boundaries.

## Security Posture

- URL/proxy validation blocks unsafe private/loopback patterns.
- Output templates and filenames are sanitized for traversal/injection safety.
- Config writes are atomic and permissions are restricted where supported.
