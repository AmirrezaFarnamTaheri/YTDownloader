# StreamCatch Internal API

## QueueManager
The `QueueManager` is the central hub for download tasks.

### Methods
- `add_item(item: dict)`: Adds a new download item.
- `get_item(id: str)`: Retrieves an item by ID.
- `claim_next_downloadable()`: (Thread-Safe) Finds the next 'Queued' item and marks it 'Processing'.

## Downloader
The `downloader` package handles the actual bits.

### Core
- `download_video(url, ...)`: The main function.
