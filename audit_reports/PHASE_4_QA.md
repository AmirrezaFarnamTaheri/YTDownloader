# Audit Report: Phase 4 - Quality Assurance & Test Engineering

## Status: 📅 Planned

**Goal:** Achieve >90% code coverage and ensure regression-free releases through comprehensive automated testing.

## 4.1 Test Architecture
**Strategy:** Use `pytest` with `pytest-mock` and `pytest-cov`.
**Mocking:** `tests/conftest.py` is the backbone. It mocks `flet`, `yt_dlp`, `pypresence`, `requests`, `PIL`, etc. This allows tests to run in environments without GUI support or external dependencies.

## 4.2 Unit Testing (`tests/unit/`)
**Objective:** Verify individual components in isolation.

*   **`batch_importer.py` Tests:**
    *   `test_import_txt_valid`: Create temp `.txt` with 3 valid URLs. Assert returns (3, False).
    *   `test_import_security_violation`: Create file outside home dir (e.g., `/tmp`). Assert `ValueError`.
    *   `test_import_limit`: Create file with 105 lines. Assert returns (100, True).
*   **`rate_limiter.py` Tests:**
    *   `test_bucket_refill`: Consume tokens, sleep `1/rate`, check tokens increased.
    *   `test_burst`: Consume `capacity` tokens instantly (should succeed). Consume 1 more (should fail).
*   **`ui_utils.py` Tests:**
    *   `test_validate_proxy_private`: Input `http://192.168.1.1:8080`. Assert `False`.
    *   `test_validate_output_template_traversal`: Input `../video`. Assert `False`.

## 4.3 Integration Testing (`tests/integration/`)
**Objective:** Verify interaction between modules.

*   **Flow: Download Cycle**
    *   **Setup:** Mock `GenericDownloader.download` to write a dummy file and call `progress_hook`.
    *   **Action:** `queue_manager.add_item(...)`.
    *   **Verify:**
        1.  Status becomes "Allocating" -> "Downloading".
        2.  `progress_hook` updates `item["progress"]`.
        3.  Mock `download` completes.
        4.  Item status -> "Completed".
        5.  `HistoryManager` has new entry.
*   **Flow: Persistence**
    *   **Action:** Modify config (`theme_mode="Light"`). Call `save_config`.
    *   **Verify:** Read file from disk, assert JSON content matches.

## 4.4 UI Testing
**Objective:** Verify UI logic and state updates.

*   **Headless Strategy:**
    *   Use `MockPage` from `conftest.py`.
    *   Instantiate `DownloadView(page)`.
    *   **Test Case:**
        *   Call `view.url_input.value = "http://test.com"`.
        *   Call `view.add_btn.on_click()`.
        *   Assert `controller.on_add_to_queue` called with "http://test.com".

## 4.5 Continuous Integration
**Objective:** Automate testing.

*   **GitHub Actions (`verify.yml`):**
    *   **Linting:** `pylint`, `black --check`, `isort --check`.
    *   **Type Checking:** `mypy .`.
    *   **Tests:** `pytest --cov=. --cov-report=xml`.
    *   **Threshold:** Fail if coverage < 85%.
