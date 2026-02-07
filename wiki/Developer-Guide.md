# Developer Guide

## Architecture

StreamCatch is designed for **Robustness**, **Modularity**, and **Speed**.

### Core Stack
-   **Language**: Python 3.10+ (Modern type hints with `from __future__ import annotations`).
-   **UI Framework**: [Flet](https://flet.dev) (Flutter for Python). Provides a native-feel, 60FPS UI with Material Design 3.
-   **Engine**: `yt-dlp` (Media Extraction) + `requests` (Generic Fallback) + `aria2c` (External Accelerator support).
-   **Data**: `SQLite` (WAL mode enabled) for high-concurrency history management.
-   **Quality Tools**: `ruff`, `black`, `isort`, `mypy`, `pylint` for code quality enforcement.

### Module Breakdown

| Module | Responsibility | Key Features |
| :--- | :--- | :--- |
| `main.py` | Entry Point | App lifecycle, Flet page initialization, Global Exception Handling. |
| `downloader.core` | Logic Hub | Orchestrates extraction strategy. Decides between `yt-dlp`, `Telegram`, or `Generic`. |
| `queue_manager.py` | Concurrency | Thread-safe Producer-Consumer queue using `threading.Lock`. Handles status updates atomically. |
| `history_manager.py` | Persistence | SQLite interface with automatic migrations and "Locked" retry logic. |
| `clipboard_monitor` | Background | Watches system clipboard for URLs (Cross-platform via `pyperclip`). |
| `views/` | UI Components | Modular screens (`DownloadView`, `QueueView`, etc.) inheriting from `BaseView`. |

## Setup

### Prerequisites
-   Python 3.10+ (as specified in pyproject.toml)
-   Git

### Installation
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
    cd YTDownloader
    ```

2.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # or
    venv\Scripts\activate     # Windows
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

4.  **Run the App**:
    ```bash
    python main.py
    ```

## Testing
StreamCatch maintains high code coverage.

```bash
# Run all tests
python -m pytest

# Check coverage
python -m pytest --cov=.
```

## Building

We use **Nuitka** to compile StreamCatch into a standalone native executable (not a Python wrapper).

### Windows
```powershell
python scripts/build_installer.py
```
This generates an `.exe` in `dist/`.

### Linux
```bash
python scripts/build_installer.py
# To build a .deb package (requires build-desktop.yml workflow locally or on CI)
```

### Mobile (Android/iOS)
Mobile builds use **Flet + Flutter** (`flet build apk/ipa`) to produce native mobile apps.

## Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes.
4.  Ensure `pylint`, `black`, and `mypy` pass.
5.  Push to the branch.
6.  Open a Pull Request.

Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for more details.
