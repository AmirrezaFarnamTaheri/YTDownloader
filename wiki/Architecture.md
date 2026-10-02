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

### Theming

`theme.py` holds two palettes and exposes the active one through `Theme.*`
class attributes plus the legacy nested proxies (`Theme.Text.PRIMARY`,
`Theme.Primary.MAIN`, …). `Theme.apply_theme_mode()` swaps the active palette.

Because Flet controls capture colour values when they are constructed, a theme
change cannot be applied by calling `update()` on existing controls. The
Settings view therefore calls back into `UIManager.refresh_theme()`, which
rebuilds the view tree with the remembered callbacks and re-mounts the new
layout on the page. That also means any new view must be built from `Theme.*`
values rather than hard-coded colours.

## Application State

- `app_state.py` owns shared managers and app-level state.
- `app_controller.py` handles UI actions and dispatches queue/download work.
  Its background loop also repaints the queue view while downloads are active
  so progress bars track real progress instead of refreshing only on events.
- `queue_manager.py` owns queue item lifecycle, cancellation tokens, ordering,
  and listener notifications. It keeps an auxiliary `id -> item` index next to
  the ordered list so the high-frequency progress updates from active
  downloads are O(1) instead of scanning the whole queue. The index is
  self-healing: a lookup that misses falls back to a linear scan and repairs
  itself.
- `tasks.py` runs background download jobs and queue processing.

Queue processing drains available concurrency slots each wake cycle so pending
items do not ramp up one at a time unnecessarily. Concurrency is enforced by a
semaphore that can be swapped at runtime from Settings; the worker pool itself
is a single long-lived `ThreadPoolExecutor`, so changing the setting never
orphans in-flight jobs or leaks threads. Each submitted job holds a reference to
the semaphore that admitted it and releases exactly that one on completion.

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

- `app_paths.py` resolves the per-user data directory (`~/.streamcatch` by
  default, relocatable with `STREAMCATCH_DATA_DIR`). The configuration, the
  history database, and the log file all live there; the test suite points the
  variable at a temporary folder so tests never touch real user data.
- `config_manager.py` handles config validation and atomic writes.
- `history_manager.py` stores history in SQLite. `export_to_json` /
  `import_from_json_file` back the History view's Export/Import buttons;
  imports skip entries already present and keep original download timestamps.
- `rss_manager.py` stores feed configuration and parses feeds safely.
- `sync_manager.py` exports/imports sanitized state and runs auto-sync.
- `cloud_manager.py` handles cloud provider integration.

Generated runtime files are ignored and should not be committed.

Controls that are refreshed from timers (queue rows, the queue view) must repaint
through `ui_utils.safe_update()`, which skips controls that are not attached to a
page; a plain `Control.update()` raises for a view that was never mounted.

## Build and Release

- `scripts/build_installer.py` builds desktop binaries with Nuitka.
- `installers/setup.iss` creates the Windows installer.
- `scripts/build_mobile.py` wraps Flet mobile builds.
- `.github/workflows/` runs verification and packaging in CI.

Windows release packaging is intentionally onefile-first: the installer places
only `StreamCatch.exe` in the app directory, while Nuitka embeds app data.
