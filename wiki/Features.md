# Feature Matrix

## Download Capabilities

- `yt-dlp` integration for broad website support.
- Telegram public link extraction pipeline.
- Generic direct-file fallback with resume + retries.
- Audio extraction, subtitle selection, chapter split support.
- Time-range clipping for partial downloads.

## Queue and Scheduling

- Full queue lifecycle tracking with status transitions.
- Reordering, retry, cancel item, cancel all.
- Pause-all and resume-all queue controls.
- Scheduled downloads with automatic transition to queued state.
- Configurable concurrency via runtime settings.

## Dashboard and UI

- Quick actions for navigation and imports.
- Download statistics (active/queued/completed/failed + success rate).
- Activity chart (rolling 7-day history).
- System health chips (FFmpeg, sync, concurrency, cache, disk free).
- Responsive layout (rail vs mobile bottom navigation).

## Data and Persistence

- SQLite history storage with indexes + WAL mode.
- Export/import settings and history.
- Safe backup/restore with traversal protections.
- Localization support (`en`, `es`, `fa`).

## Integrations

- RSS feed ingestion.
- Discord Rich Presence integration.
- Google Drive cloud backup integration (via PyDrive2).

## Security and Hardening

- URL/proxy validation with private-network restrictions.
- Path sanitization for output templates and filenames.
- Atomic config writes and restrictive permissions where possible.
- Zip-slip checks during import.

## Packaging

- Desktop native build path (Nuitka).
- Windows installer packaging (Inno Setup).
- Android APK build path (Flet build tooling).
