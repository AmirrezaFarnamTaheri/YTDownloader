# Audit Report: Phase 2 - Core Architecture 2.0

## Status: 🚧 In Progress

This phase focuses on enhancing the application's data persistence, network resilience, and security mechanisms.

## 2.1 Advanced Data Management
**Goal:** Improve database reliability and configuration validation.

*   **Status:** **Completed**
*   **Implementation Details:**
    *   **ConfigManager (`config_manager.py`):**
        *   **Atomic Writes:** Uses `tempfile.mkstemp` (with `0o600` permissions) to write the new config, then uses `os.replace` (atomic on POSIX, mostly atomic on Windows) to swap it with the target file. This prevents file corruption if the app crashes during write.
        *   **Schema Validation:** `_validate_schema` enforces strict types (e.g., `use_aria2c` must be `bool`, `metadata_cache_size` must be `int > 0`). It specifically validates `output_template` to ensure it is relative and contains no `..` traversal.
        *   **Error Recovery:** If `json.load` fails, the corrupted file is renamed to `.bak`, and defaults are loaded.
    *   **HistoryManager (`history_manager.py`):**
        *   **WAL Mode:** Enables `PRAGMA journal_mode=WAL` to allow concurrent readers and writers, significantly reducing `database is locked` errors.
        *   **Vacuuming:** `vacuum()` method explicitly shrinks the DB file.
        *   **Schema Migration:** Automatically checks for missing columns (e.g., `file_path`) and adds them via `ALTER TABLE`.
        *   **Retry Logic:** Wraps operations in a loop (max 3 retries) with backoff if the DB is locked.
*   **Impact:** Zero config corruption incidents; smoother history access during heavy downloads.

## 2.2 Network Engine Refinement
**Goal:** Improve network efficiency and handle failures gracefully.

*   **Status:** **Partially Completed**
*   **Implementation Details:**
    *   **RateLimiter (`rate_limiter.py`):** **Completed.**
        *   **Algorithm:** Token Bucket.
        *   **Math:** `tokens = min(capacity, tokens + (elapsed * rate))`.
        *   **Logic:** Allows short bursts (up to `capacity`) but throttles sustained activity to `rate`. Thread-safe via `threading.Lock`.
    *   **BatchImporter (`batch_importer.py`):** **Needs Improvement.**
        *   *Current State:* Reads `.txt`/`.csv` line-by-line. Synchronously validates each URL using `validate_url` (regex + logic). Adds to queue.
        *   *Limitation:* Max 100 items per batch. No async verification (checking if link is live) before adding.
        *   *Recommended Upgrade:* Use `concurrent.futures.ThreadPoolExecutor` to perform HEAD requests on URLs to filter dead links *before* queuing them.
    *   **SocialManager (`social_manager.py`):** **Basic.**
        *   *Current State:* Connects to Discord RPC. Updates activity. Has basic `try/except`.
        *   *Risk:* If Discord is not running or RPC fails, it logs warnings. Repeated failures could spam logs.
        *   *Recommended Upgrade:* Implement a "Circuit Breaker" that disables the manager after 3 consecutive failures for a set cooling-off period (e.g., 5 minutes).
    *   **ClipboardMonitor (`clipboard_monitor.py`):** **Basic.**
        *   *Current State:* Background thread loops every 2 seconds. Checks `pyperclip.paste()`.
        *   *Risk:* Constant polling even when idle.
        *   *Recommended Upgrade:* Exponential backoff (sleep 2s, then 4s, up to 30s) if no change is detected, resetting on user activity.

## 2.3 Security Hardening
**Goal:** Prevent advanced network attacks and secure sensitive data.

*   **Status:** **Pending Verification / Partial**
*   **Implementation Details:**
    *   **SSRF Protection (`ui_utils.py`):**
        *   **Current Logic:** `validate_url` and `validate_proxy` parse the hostname.
        *   **Checks:**
            1.  Explicitly blocks `localhost`, `127.0.0.1`, `::1`.
            2.  Uses `ipaddress.ip_address(hostname)` to check `.is_private` or `.is_loopback`.
            3.  Regex fallback to catch numeric IPs like `1.2.3.4` if `ipaddress` parsing fails or isn't attempted on a string.
        *   **Gap:** Does not resolve DNS. If `malicious.com` resolves to `127.0.0.1`, the current check passes (as it checks the string "malicious.com").
        *   **Fix Required:** Must perform a DNS resolution on the hostname *before* allowing the connection (or rely on `requests` hooks to validate the target IP).
    *   **Cookie Encryption:** **Not Started.**
        *   *Status:* Cookies are stored in plain text or passed via browser.
        *   *Requirement:* Integrate `cryptography` library. Generate a local key (e.g., using `machine-id` + user salt). Encrypt sensitive fields in `config.json`.
    *   **Path Traversal:** **Robust.**
        *   `GenericDownloader` and `ConfigManager` both use `os.path.commonpath` to ensure paths remain within approved directories.
