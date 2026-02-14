# StreamCatch

StreamCatch (formerly YTDownloader) is a production-focused media downloader built with [Flet](https://flet.dev) + [yt-dlp](https://github.com/yt-dlp/yt-dlp), with queue orchestration, scheduling, history, cloud sync, and multi-platform packaging.

![StreamCatch Banner](assets/logo.svg)

## Highlights

- Multi-source downloads: YouTube + thousands of yt-dlp sites, Telegram public links, and direct file fallback.
- Advanced queue lifecycle: queued/scheduled/allocating/downloading/processing/completed/error/cancelled.
- Desktop-first UX: dashboard, queue controls, history, RSS, settings, localization, and accessibility options.
- Security-conscious defaults: URL/proxy validation, path safety checks, config atomic writes, zip-slip protection.
- Packaging pipeline: desktop native builds (`.exe`, `.dmg`, `.deb`) and mobile Android build (`.apk`).

## Documentation

- Wiki Home: [wiki/Home.md](wiki/Home.md)
- Installation: [wiki/Installation.md](wiki/Installation.md)
- User Guide: [wiki/User-Guide.md](wiki/User-Guide.md)
- Developer Guide: [wiki/Developer-Guide.md](wiki/Developer-Guide.md)
- Architecture: [wiki/Architecture.md](wiki/Architecture.md)
- API: [wiki/API.md](wiki/API.md)
- Troubleshooting: [wiki/Troubleshooting.md](wiki/Troubleshooting.md)

## Quick Start (Source)

```bash
git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
cd YTDownloader
python3 -m pip install -r requirements.txt
python3 main.py
```

## Build Outputs

### Desktop Native (EXE/DMG/Linux Binary)

```bash
python3 scripts/build_installer.py
```

- Windows output: `dist/StreamCatch.exe` (+ Inno Setup installer if `iscc` is available)
- Linux output: `dist/streamcatch` (CI also packages `.deb`)
- macOS output: `dist/StreamCatch.app` (CI also packages `.dmg`)

### Android APK

```bash
python3 scripts/build_mobile.py --target apk
```

- APKs are discovered under `build/` and printed by the script after build.
- For CI/release automation, see `.github/workflows/build-mobile-flet.yml`.

## Validation Commands

```bash
python3 -m pytest -q -s
mypy .
ruff check . --exclude tests
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

AGPL-3.0. See [LICENSE](LICENSE).
