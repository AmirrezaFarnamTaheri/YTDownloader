# Project Health

This document records the current engineering baseline for StreamCatch. It is
intended to stay factual and current; older one-off audit and finalization
reports were removed because they no longer matched the codebase after the
stability and packaging work.

## Current Status

- Desktop app: Flet-based StreamCatch UI with dashboard, queue, history, RSS,
  settings, profiles, metadata preview, scheduling, and cloud sync.
- Downloader backend: yt-dlp first, Telegram public links, and direct-file
  fallback with redirect-aware URL safety checks.
- Packaging: Nuitka onefile desktop build by default. On Windows, the Inno Setup
  installer installs the single compiled `StreamCatch.exe`; assets and locales
  are embedded into the executable by the Nuitka build.
- Tests: broad mocked unit/integration coverage for controllers, queue logic,
  download options, URL safety, RSS, sync, localization, and build helpers.

## Verification Baseline

Run before release:

```bash
python -m compileall .
pytest -q
git diff --check
python scripts/build_installer.py --dry-run --skip-installer
python scripts/build_mobile.py --target apk --dry-run
python -m ruff check .
python -m mypy .
```

Known local-environment limits:

- The local test environment may mock Flet if real `flet` is not installed.
- `ruff`, `mypy`, and packaging tools must be installed from
  `requirements-dev.txt` before those checks can run locally.
- A real release build requires the full Python runtime requirements, Nuitka,
  and a native compiler/toolchain. Windows installer generation also requires
  Inno Setup.

## Release Expectations

- Generated artifacts are not tracked in git: `dist/`, `build/`,
  `installers/output/`, `build_logs/`, logs, `.exe` files, test databases, and
  temporary export/backup files are ignored.
- Release artifacts should be attached to GitHub Releases, not committed.
- The Windows installer should contain only the onefile executable. Runtime data
  such as `assets/` and `locales/` is bundled into the executable.

## Remaining Manual Checks

- Run the app once with real Flet installed and verify the main navigation,
  queue actions, settings saves, and metadata preview.
- Run at least one real yt-dlp download with FFmpeg installed.
- Build a real Windows installer with Inno Setup and launch the installed app
  from the Start Menu.
