# StreamCatch

StreamCatch is a desktop-first media downloader built with Flet and yt-dlp. It
combines a queue manager, metadata preview, download profiles, history, RSS
feeds, scheduling, cloud sync, localization, and native packaging.

![StreamCatch Banner](assets/logo.svg)

## What It Does

- Downloads from YouTube and other yt-dlp-supported sites.
- Handles Telegram public media links and direct file URLs.
- Supports search input through yt-dlp search targets.
- Provides queue controls for start, cancel, retry, reorder, pause/resume, and
  concurrent processing, with live progress while downloads run.
- Offers download profiles, output templates, subtitles, sponsorblock,
  chapter-splitting options, and browser-cookie selection.
- Imports link lists in bulk from `.txt` or `.csv` files.
- Tracks history, recent activity, sync status, and RSS feed items.
- Ships a dark theme, a light theme, and a high-contrast mode; switching applies
  immediately without a restart.
- Builds as a onefile desktop executable, with a Windows installer that installs
  only the compiled EXE.

## Install

For normal use, download the latest release from:

<https://github.com/AmirrezaFarnamTaheri/YTDownloader/releases>

Windows users should prefer `StreamCatch_Setup_vX.Y.Z.exe`. The installer places
one standalone `StreamCatch.exe` on the machine; bundled app assets and locale
files are embedded during the release build.

FFmpeg is recommended for best audio/video post-processing support.

## Run From Source

```bash
git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
cd YTDownloader
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

On macOS/Linux, activate the environment with `source .venv/bin/activate`.

## Build

Desktop onefile binary:

```bash
python scripts/build_installer.py
```

Windows installer:

```bash
python scripts/build_installer.py
```

The same command builds `dist/StreamCatch.exe`; if Inno Setup is available on
Windows, it also produces `installers/output/StreamCatch_Setup_vX.Y.Z.exe`.

Android APK:

```bash
python scripts/build_mobile.py --target apk
```

## Verify

The commands below mirror the CI gate; all of them must pass before a change is
handed off.

```bash
python -m compileall .
python -m black --check .
python -m isort --check-only .
python -m ruff check . --exclude tests
python -m pylint $(git ls-files '*.py' | grep -v '^tests/')
python -m mypy --config-file mypy.ini .
pytest -q
git diff --check
python scripts/build_installer.py --dry-run --skip-installer
python scripts/build_mobile.py --target apk --dry-run
```

Install developer tooling with `python -m pip install -r requirements-dev.txt`.
Run `pytest --cov=. --cov-report=term-missing` for the coverage report; the
configured floor is 60%.

## Documentation

- [Installation](wiki/Installation.md)
- [User Guide](wiki/User-Guide.md)
- [Developer Guide](wiki/Developer-Guide.md)
- [Architecture](wiki/Architecture.md)
- [Features](wiki/Features.md)
- [Troubleshooting](wiki/Troubleshooting.md)
- [Project Health](PROJECT_HEALTH.md)

## License

AGPL-3.0. See [LICENSE](LICENSE).
