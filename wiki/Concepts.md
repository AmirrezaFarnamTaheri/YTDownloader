# Core Concepts

## Downloaders vs. Extractors

*   **Extractors**: Responsible for parsing a URL and retrieving metadata (title, thumbnail, formats). They do *not* download the media content itself.
*   **Downloaders**: Responsible for fetching the binary data and saving it to disk. They handle progress reporting, retries, and file assembly.

## The Queue System

The queue is a priority-based list of download tasks. It supports:
*   **Concurrency**: Multiple downloads running simultaneously (configurable).
*   **Persistence**: Queue state is saved to disk (in theory, though currently mostly in-memory runtime).
*   **Status Tracking**: Pending, Downloading, Completed, Error, Cancelled.

## Cancellation Tokens

We use a `CancelToken` pattern (similar to C# CancellationToken) to handle download cancellation safely across threads. The token is passed down to the downloader engine, which periodically checks `token.is_cancelled`.

## Flet & UI Threading

Flet runs on a separate thread. Updates to the UI from background threads (like download progress) must be thread-safe. We use `page.update()` or control-specific update methods.
