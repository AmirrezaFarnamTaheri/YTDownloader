# Architecture

StreamCatch is organized around a small number of responsibilities.

## UI Layer

- `main.py` starts Flet and global crash handling.
- `ui_manager.py` creates views and coordinates navigation.
- `views/` contains dashboard, download, queue, history, RSS, and settings
  screens.
- `views/components/` contains reusable controls such as the download input
  card, preview card, queue item, history item, and source-specific option
  panels.

Flet UI work that originates outside the UI thread should use
`ui_utils.run_on_ui_thread()`.

## Application State

- `app_state.py` owns shared managers and app-level state.
- `app_controller.py` handles UI actions and dispatches queue/download work.
- `queue_manager.py` owns queue item lifecycle, cancellation tokens, ordering,
  and listener notifications.
- `tasks.py` runs background download jobs and queue processing.

Queue processing drains available concurrency slots each wake cycle so pending
items do not ramp up one at a time unnecessarily.

## Downloader Layer

- `downloader/core.py` maps `DownloadOptions` into yt-dlp options.
- `downloader/engines/ytdlp.py` wraps yt-dlp execution and final file detection.
- `downloader/engines/generic.py` handles direct-file fallback downloads.
- `downloader/extractors/telegram.py` handles Telegram public media links.
- `downloader/info.py` fetches metadata with bounded waiting.

URL validation, redirect safety, filename safety, output-template validation,
rate-limit conversion, and cancellation checks are centralized rather than
implemented differently per view.

## Data and Persistence

- `config_manager.py` handles config validation and atomic writes.
- `history_manager.py` stores history in SQLite.
- `rss_manager.py` stores feed configuration and parses feeds safely.
- `sync_manager.py` exports/imports sanitized state and runs auto-sync.
- `cloud_manager.py` handles cloud provider integration.

Generated runtime files are ignored and should not be committed.

## Build and Release

- `scripts/build_installer.py` builds desktop binaries with Nuitka.
- `installers/setup.iss` creates the Windows installer.
- `scripts/build_mobile.py` wraps Flet mobile builds.
- `.github/workflows/` runs verification and packaging in CI.

Windows release packaging is intentionally onefile-first: the installer places
only `StreamCatch.exe` in the app directory, while Nuitka embeds app data.
