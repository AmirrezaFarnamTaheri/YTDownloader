# User Guide

## Add a Download

1. Open **Download**.
2. Paste a URL or search phrase.
3. Pick a profile such as Best, Fast 720p, Audio MP3, or Archive.
4. Adjust optional settings: format, subtitles, playlist handling, sponsorblock,
   chapter splitting, cookies, schedule time, and output template.
5. Fetch metadata if you want a preview.
6. Add the item to the queue.

Search phrases are sent through yt-dlp search support. Direct URLs are validated
before they enter the queue.

## Queue

The queue shows each item state:

- queued
- scheduled
- allocating
- downloading
- processing
- completed
- error
- cancelled

Use queue actions to cancel, retry, remove, reorder, pause, resume, open output
folders, and inspect active progress. Concurrency is controlled by settings and
the queue worker fills available slots as they open.

## Profiles

Profiles apply practical defaults:

- Best: highest available quality.
- Fast 720p: quicker video downloads.
- Audio MP3: audio extraction workflow.
- Archive: durable archival defaults.

You can still override profile-derived settings per item.

## History

History records completed and failed downloads. Use live search to filter by
title, URL, or status. History can be cleared or exported from the app.

## RSS

RSS feeds can be added from the RSS view. Feed items can be opened or added to
the download queue.

## Sync

Sync can export/import app state and optionally use cloud storage. Sensitive
fields such as cookies and tokens are stripped from sync payloads before export.

## Settings

Important settings include:

- download folder;
- concurrency;
- rate limit;
- output template;
- theme and compact mode;
- clipboard monitoring;
- auto-sync;
- browser-cookie source;
- FFmpeg-related behavior.

Some appearance changes may require restarting the app.

## Packaging Note

The Windows release installer installs a single standalone EXE. FFmpeg remains a
recommended system dependency for full media post-processing support.
