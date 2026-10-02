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

### Filtering a large queue

The Queue view has a search box and a status filter:

- search matches the title or the URL, case-insensitively;
- the filter narrows the list to **Active**, **Queued**, **Completed**, or
  **Failed** items.

Filters only affect what is displayed — the bulk actions (Cancel All, Pause All,
Resume All, Clear Completed) always apply to the whole queue, and the statistics
line always describes the whole queue.

## Profiles

Profiles apply practical defaults:

- Best: highest available quality.
- Fast 720p: quicker video downloads.
- Audio MP3: audio extraction workflow.
- Archive: durable archival defaults.

You can still override profile-derived settings per item.

## Batch Import

Use **Batch Import** in the Download view (or the Dashboard quick action) to
queue many links at once. The picker accepts:

- `.txt` — one URL per line;
- `.csv` — the first non-empty cell of each row is treated as a URL, so files
  exported from a spreadsheet work directly.

Files are limited to 5 MB and 100 links per import. Each link is verified with a
HEAD request before it is queued, and the queue stops accepting the batch if it
reaches its 1000-item cap. Invalid or unreachable links are skipped.

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
- theme (Dark, Light, System, High Contrast) and compact mode;
- clipboard monitoring;
- auto-sync;
- browser-cookie source;
- FFmpeg-related behavior.

Changing the theme rebuilds the interface immediately — no restart required.
The download volume shown on the Dashboard is the folder configured here, so
storage figures and health chips always describe where files will land.

## Backing Up History

The History view has **Export History** and **Import History** buttons:

- **Export History** writes the full history (up to 10,000 entries) to a JSON
  file you choose.
- **Import History** restores such a file. Entries already present are skipped,
  so importing the same backup twice does not duplicate anything, and each
  restored entry keeps its original download date.

## Keyboard Shortcuts

While the Queue view is open:

- `J` / `K` — move the selection down / up;
- `Delete` — remove the selected item from the queue.

These keys are ignored while another view is displayed, so browsing the
Dashboard or Settings cannot change queue selection by accident.

## Packaging Note

The Windows release installer installs a single standalone EXE. FFmpeg remains a
recommended system dependency for full media post-processing support.
