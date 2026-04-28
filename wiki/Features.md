# Features

## Downloads

- YouTube and yt-dlp-supported sites.
- Telegram public media links.
- Direct file fallback downloader.
- Search input through yt-dlp search targets.
- Metadata preview before queueing.
- Per-item output templates and filenames.
- Browser-cookie source selection.
- Subtitle language selection.
- SponsorBlock and chapter splitting options.
- Numeric yt-dlp rate-limit conversion from user-friendly values such as `5M`.

## Queue

- Concurrent background processing.
- Scheduled downloads.
- Cancel, retry, remove, reorder, pause, and resume.
- Progress, speed, size, filename, and status updates.
- Cancellation token registration per item.

## Library

- Download history.
- Live history search.
- Activity and status stats.
- RSS feeds with add-to-queue actions.

## Sync and Settings

- Config validation and atomic saves.
- Secure cookie storage through keyring when available.
- Sanitized sync/export that strips secrets.
- Auto-sync lifecycle controls.
- Cloud sync integration.
- Theme, compact mode, output folder, concurrency, and rate-limit settings.

## Packaging

- Nuitka desktop builds.
- Windows onefile installer.
- Linux/macOS packaging paths in CI.
- Android APK/AAB and iOS IPA build script support.
