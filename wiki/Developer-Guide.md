# Developer Guide

## Prerequisites

- Python 3.10+ (tested with 3.10, 3.11, 3.12)
- Git
- FFmpeg (recommended)
- Optional:
  - `aria2c` for accelerated downloads
  - Flutter toolchain for mobile packaging
  - Inno Setup for Windows installer generation

## Local Setup

```bash
git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
cd YTDownloader
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
```

Run app:

```bash
python3 main.py
```

## Validation Workflow

Run this before a PR:

```bash
python3 -m pytest -q -s
mypy .
ruff check . --exclude tests
TMPDIR=/tmp python3 -m black --check .
isort --check-only .
```

## Test Strategy

- Unit-heavy test suite with extensive mocking around Flet and integration boundaries.
- Queue, task, downloader, sync, and UI controller coverage is prioritized.
- Add regression tests for any bug fixes in threading, queue transitions, or callback timing.

## Build Targets

### Desktop Native (Nuitka)

```bash
python3 scripts/build_installer.py
```

Outputs:

- Linux: `dist/streamcatch`
- macOS: `dist/StreamCatch.app`
- Windows: `dist/StreamCatch.exe` (+ installer if Inno Setup exists)

### Android APK / Mobile

```bash
python3 scripts/build_mobile.py --target apk
```

Useful options:

```bash
python3 scripts/build_mobile.py --target aab
python3 scripts/build_mobile.py --target ipa
python3 scripts/build_mobile.py --target apk --skip-requirements-swap
```

## CI/CD

Primary workflows:

- `verify.yml`: lint, type-check, tests, and dependency vulnerability check.
- `build-desktop.yml`: matrix desktop binary builds.
- `build-mobile-flet.yml`: Android/iOS build pipeline.
- `release.yml`: orchestrates builds and attaches artifacts to GitHub Release.

## Coding Conventions

- Type annotations for public interfaces.
- Explicit lifecycle/state transitions for queue operations.
- Fail safely with logs at integration boundaries.
- Keep UI logic thin; business logic belongs to managers/tasks/downloader modules.

## Release Flow

1. Create/merge release-ready changes into `main`.
2. Tag version (`vX.Y.Z`).
3. GitHub Actions builds desktop/mobile artifacts.
4. Release workflow publishes binaries (`.exe`, `.deb`, `.dmg`, `.apk`).
