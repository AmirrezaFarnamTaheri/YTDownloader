# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-11-09 - Comprehensive Refactor & Quality Release

### Added
- **Type Hints**: Full Python type annotations throughout codebase
- **Configuration Persistence**: Settings saved to `~/.ytdownloader/config.json`
- **Theme Preference**: User theme choice (light/dark) persists between sessions
- **Input Validation**: URL, proxy, rate limit, and output path validation
- **Enhanced Logging**: INFO and DEBUG level logging to `ytdownloader.log`
- **Error Handling**: Comprehensive exception handling with user-friendly messages
- **Utility Functions**: `validate_url()`, `validate_proxy()`, `validate_rate_limit()`, `format_file_size()`
- **Safe Format ID Extraction**: New `_extract_format_id()` method with fallback handling
- **Socket Timeout**: 30-second timeout for video info fetching
- **Directory Creation**: Automatic output directory creation if needed
- **Status Messages**: Queue size indicators in status bar
- **Confirmation Dialogs**: User confirmation for destructive operations
- **Improved Documentation**: Comprehensive README with testing, architecture, troubleshooting
- **Extended Test Suite**: 40+ unit tests covering functionality, edge cases, error handling

### Fixed
- **Critical Bug**: Fixed CancelToken missing `is_paused` initialization (AttributeError)
- **Critical Bug**: Fixed file size division by zero when `filesize` is None
- **Critical Bug**: Fixed IndexError crashes in queue operations (remove, cancel, open)
- **Critical Bug**: Fixed unsafe format ID parsing with fragile string split
- **Thread Safety**: Fixed race conditions with daemon threads
- **Error Messages**: Improved user-facing error messages with log file references
- **Logging**: Changed from ERROR-only to INFO level (better diagnostics)
- **Icon Handling**: Graceful handling of missing icon file
- **Thumbnail Fetching**: Added timeout and error handling for thumbnail requests

### Changed
- **Window Sizing**: Set minimum window size to 900x700 for better usability
- **Title**: Updated window title to "YTDownloader - Advanced YouTube Video Downloader"
- **Code Organization**: Refactored configuration management into separate functions
- **Format Strings**: Improved format display with proper file size formatting
- **Error Handling**: More specific exception handling for different error types
- **Pause Interval**: Changed from 1 second to 0.5 seconds for more responsive pause/resume
- **Constants**: Extracted magic numbers into named constants (THUMBNAIL_SIZE, WINDOW_MIN_WIDTH, etc.)
- **Docstrings**: Added comprehensive docstrings with Args, Returns, Raises sections
- **Test Framework**: Expanded from minimal tests to comprehensive 40+ test suite

### Improved
- **Code Quality**: Better separation of concerns, reduced coupling
- **Maintainability**: Type hints and comprehensive docstrings
- **Reliability**: Proper exception handling in all critical operations
- **User Experience**: Better status messages and confirmation dialogs
- **Performance**: Optimized pause/resume sleep interval
- **Documentation**: Comprehensive README with examples and troubleshooting

### Dependencies
- Updated requirements.txt with specific version constraints
- Added development dependencies (pytest, pytest-cov, etc.)
- Added optional quality tools (black, mypy, pylint)

## [1.0.0] - Initial Release

### Features
- Modern Tkinter GUI with sv-ttk theme support
- Download single videos and entire playlists
- Format selection with detailed specifications
- Subtitle and transcript downloading
- Chapter splitting support
- Proxy configuration
- Download speed limiting
- Download queue management with pause/resume/cancel
- Real-time progress tracking
- Video information preview
- Custom output path selection

### Known Limitations
- No configuration persistence
- Limited error handling
- Basic test coverage
- Limited input validation
