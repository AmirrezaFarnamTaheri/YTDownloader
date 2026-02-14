# User Guide

## Main Views

- **Dashboard**: health summary, recent history, and quick actions.
- **Download**: URL entry, metadata fetch, format/options selection.
- **Queue**: lifecycle management, pause/resume/cancel/retry, item actions.
- **History**: persistent record with search/export/import utilities.
- **RSS**: feed monitoring and enqueue integration.
- **Settings**: theme, language, concurrency, network, paths, accessibility.

## Standard Download Workflow

1. Paste URL in **Download** view.
2. Click **Fetch Info**.
3. Pick quality/options.
4. Click **Add to Queue**.
5. Track progress in **Queue**.

## Batch Workflow

1. Prepare `.txt` file (one URL per line).
2. Use **Batch Import** button.
3. Review queued items.
4. Use pause/resume/cancel controls as needed.

## Scheduled Downloads

1. Choose schedule time in Download view.
2. Add item to queue.
3. Item appears as scheduled until trigger time.

## Queue Controls

Per-item actions:

- cancel
- retry
- remove
- play/open file
- open containing folder

Bulk actions:

- clear completed
- pause all queued
- resume all paused
- cancel all active

## Settings Recommendations

- Set a writable download path.
- Keep `max_concurrent_downloads` realistic for your network/storage.
- Enable high contrast mode for accessibility.
- Configure proxy/rate-limit only when required.

## Security Notes

- Only use cookies from trusted local browser profiles.
- Avoid arbitrary import archives from untrusted sources.
- Keep the app updated for latest extractor/site compatibility.
