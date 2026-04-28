# Developer Guide

## Setup

Requirements:

- Python 3.10 or newer.
- Git.
- FFmpeg for realistic download/post-processing tests.
- Inno Setup for Windows installer builds.
- Nuitka and developer tools from `requirements-dev.txt`.

```bash
git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
cd YTDownloader
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
```

On macOS/Linux, use `source .venv/bin/activate`.

## Run

```bash
python main.py
```

For web-server mode:

```bash
FLET_SERVER_PORT=8550 python main.py --web
```

## Verification

Run the full local gate before handing off changes:

```bash
python -m compileall .
pytest -q
git diff --check
python scripts/build_installer.py --dry-run --skip-installer
python scripts/build_mobile.py --target apk --dry-run
python -m ruff check .
python -m mypy .
```

The tests provide broad coverage but may mock Flet when the real Flet runtime is
not installed. Real release validation should include at least one manual launch
with real Flet and one real yt-dlp download.

## Build System

### Desktop

```bash
python scripts/build_installer.py
```

The desktop build uses Nuitka. By default it:

- builds a standalone executable;
- uses onefile mode on Windows and Linux;
- embeds `assets/` and `locales/`;
- checks that required runtime dependencies are installed;
- explicitly includes runtime packages for release-grade bundling;
- invokes Inno Setup on Windows when `iscc` is available.

Useful environment variables:

```bash
STREAMCATCH_ONEFILE=0 python scripts/build_installer.py
STREAMCATCH_ENABLE_LTO=1 python scripts/build_installer.py
STREAMCATCH_INCLUDE_RUNTIME_PACKAGES=0 python scripts/build_installer.py
APP_VERSION=2.1.0 python scripts/build_installer.py
```

Use `STREAMCATCH_INCLUDE_RUNTIME_PACKAGES=0` only for quick local compiler
experiments, not release builds.

### Mobile

```bash
python scripts/build_mobile.py --target apk
python scripts/build_mobile.py --target aab
python scripts/build_mobile.py --target ipa
```

Mobile builds require the Flet/Flutter mobile toolchain.

## Codebase Rules

- Keep business logic in managers, tasks, and downloader modules.
- Keep UI event handlers thin and route state changes through app controllers or
  managers.
- Use `ui_utils.run_on_ui_thread()` for Flet UI callbacks from worker threads.
- Validate external URLs with the shared URL helpers.
- Do not commit generated artifacts: logs, test databases, build outputs,
  installers, exported configs, or caches.
- Add regression tests for queue, threading, sync, downloader, build, or
  validation changes.

## Release Flow

1. Update version metadata.
2. Run the verification gate.
3. Build release artifacts through GitHub Actions or a clean local toolchain.
4. Attach generated binaries/installers to a GitHub Release.
5. Do not commit release artifacts back into git.
