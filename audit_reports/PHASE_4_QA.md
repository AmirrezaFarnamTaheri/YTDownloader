# Audit Report: Phase 4 - Quality Assurance & Test Engineering

## Status: 📅 Planned

**Goal:** Achieve >90% code coverage and ensure regression-free releases through comprehensive automated testing.

## 4.1 Unit Testing (`tests/unit/`)
**Objective:** Verify individual components in isolation.

*   **Target: `batch_importer.py`**
    *   **Tests:**
        *   `test_parse_txt`: Verify parsing of standard newline-separated URL lists.
        *   `test_parse_csv`: Verify parsing of CSV files (handling delimiters).
        *   `test_parse_invalid`: Ensure the parser gracefully handles garbage data, empty lines, and non-UTF-8 files.
*   **Target: `social_manager.py`**
    *   **Tests:**
        *   `test_connect_timeout`: Mock `pypresence.connect` to hang or fail, ensure `SocialManager` handles it without crashing the app.
        *   `test_update_activity`: Verify `update()` calls with correct arguments.
*   **Target: `rate_limiter.py`**
    *   **Tests:**
        *   `test_token_bucket_refill`: Ensure tokens regenerate over time.
        *   `test_burst_handling`: Verify `wait()` blocks correctly when bucket is empty.

## 4.2 Integration Testing (`tests/integration/`)
**Objective:** Verify interaction between modules.

*   **`test_full_lifecycle.py`:**
    *   **Scenario:** Add URL -> Queue -> Download -> History.
    *   **Steps:**
        1.  Call `AppController.on_add_to_queue(url)`.
        2.  Assert item appears in `QueueManager`.
        3.  Wait for `Task` to complete (mocking the actual network call).
        4.  Assert item moves to `HistoryManager`.
        5.  Assert `HistoryManager` contains the record.
*   **`test_persistence.py`:**
    *   **Scenario:** Application Restart.
    *   **Steps:**
        1.  Add items to queue.
        2.  Call `AppState.save()`.
        3.  Destroy `AppState` instance.
        4.  Create new `AppState` instance and load.
        5.  Verify queue items are restored with correct status.

## 4.3 UI Testing
**Objective:** Verify UI logic and state updates.

*   **Headless Testing:**
    *   Since Flet runs a server, full E2E UI testing can be complex. We will use a "Mock Page" approach.
    *   **`MockPage` Class:** Implement `add`, `update`, `clean`, `controls` list.
    *   **Scenario:**
        1.  Instantiate `DownloadView` with `MockPage`.
        2.  Call `download_view.add_item("http://test.com")`.
        3.  Assert `len(mock_page.controls) > 0`.
        4.  Simulate "Click" on "Download" button.
        5.  Assert `AppController.start_download` was called.

## 4.4 Continuous Integration
**Objective:** Automate testing on every push.

*   **GitHub Actions (`verify.yml`):**
    *   Add `pytest --cov=streamcatch --cov-report=xml` step.
    *   Add `codecov` upload (optional).
    *   Fail build if coverage drops below 85%.
