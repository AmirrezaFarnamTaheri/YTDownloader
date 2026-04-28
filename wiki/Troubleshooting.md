# Troubleshooting

## App Does Not Start

Run from a terminal:

```bash
python main.py
```

Check the log file and crash output. If running from source, confirm
dependencies are installed:

```bash
python -m pip install -r requirements.txt
```

## Metadata Fetch Fails

- Confirm the URL is public and reachable.
- Try browser cookies for sites that require login.
- Try adding the item to the queue anyway if the source supports direct
  download through yt-dlp.
- Update yt-dlp.

```bash
python -m pip install -U yt-dlp
```

## Downloads Fail During Post-Processing

Install FFmpeg and make sure it is on `PATH`.

```bash
ffmpeg -version
```

## Windows Installer Is Missing

`scripts/build_installer.py` always tries to build the standalone EXE. The Inno
Setup installer is produced only when `iscc` is installed and discoverable.

```bash
python scripts/build_installer.py --dry-run --skip-installer
```

## Build Fails Before Nuitka Starts

The build script checks runtime dependencies for self-contained releases. Install
requirements:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Tests Say Flet Is Mocked

That means the local environment does not have real Flet installed. The test
suite can still validate most logic, but a release pass should include a manual
launch with real Flet installed.

## Sync Export Contains No Cookies

That is expected. Sync/export strips cookies, tokens, passwords, and similar
secrets before writing payloads.
