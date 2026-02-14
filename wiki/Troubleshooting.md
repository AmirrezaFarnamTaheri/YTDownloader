# Troubleshooting

## Build Issues

### `Nuitka not installed` / desktop build fails

```bash
python3 -m pip install -r requirements-dev.txt
```

Then rerun:

```bash
python3 scripts/build_installer.py
```

### `Flet CLI not found` during APK build

Ensure mobile requirements are installed and `flet` is on PATH:

```bash
python3 -m pip install -r requirements-mobile.txt
python3 scripts/build_mobile.py --target apk
```

## Runtime Issues

### FFmpeg missing

Symptoms: merge/postprocess/subtitle embedding fails.

- Windows: add `ffmpeg.exe` to PATH.
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`

### Metadata fetch fails

- Verify URL in browser first.
- Try browser-cookie selection for restricted content.
- Try `Force Generic` for direct-file links.

### Download starts then errors

- Check proxy/rate-limit settings.
- Validate free disk space.
- Confirm output path exists and is writable.

## Queue/UI Issues

### Queue appears stuck

- Check if items are `Paused` and press `Resume All`.
- Check if items are `Scheduled` for a future time.
- Review logs for throttling or network errors.

### Blank/incorrect UI state

- Resize app window to force layout refresh.
- Toggle theme mode once in Settings.
- Restart app after changing language.

## Sync/Import Issues

### Import rejected due invalid archive

- Ensure zip contains `config.json` and optional `history.db`.
- Avoid archives with nested/unsafe paths.

### Cloud auth failures

- Ensure Google credentials file exists at configured path.
- In CI/headless, pre-provision credentials where interactive auth is impossible.

## Logs

- App logs: `ytdownloader.log`
- Crash reports:
  - Linux/macOS: `~/.streamcatch/crash.log`
  - Windows: `%USERPROFILE%\.streamcatch\crash.log`

When opening an issue, include:

- OS + app version
- Steps to reproduce
- Relevant log excerpts
