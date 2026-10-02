# StreamCatch Audit and Redesign — Working Notes

Revision audited: `c412190` (`main`) → branch `arena/01a0fd65-ytdownloader`
(the branch contains the complete change set described here).

Scope: backend architecture and downloader package, UI/UX and view layer, state
management, data flows, configuration, packaging, documentation, tests,
security, reliability, and performance of the desktop app.

## Method and evidence tiers

Every claim below is labelled with the strongest evidence available:

| Tier | Meaning |
| --- | --- |
| **T1** | Executed in this workspace: command output, measured numbers, a test that failed before a change and passed after. |
| **T2** | Static reading of the repository at an exact anchor (file, symbol). |
| **T3** | Inference from adjacent code; not directly executed. Flagged as such wherever used. |

Rules applied: no finding is reported as a vulnerability without tracing the path
from input to effect; behaviour changes are proven by a regression test where one
is feasible; a fix that would break algorithm semantics is not treated as an
optimization; subsystems were not removed before checking CI, packaging, and
documentation references.

Baseline (before changes): 320 tests, 1 pre-existing failure
(`tests/test_youtube_panel.py::test_archive_profile_updates_controls`),
75% statement coverage.

Final state (T1): **512 tests pass**, **77% statement coverage**, `black`,
`isort`, `ruff`, `mypy`, and `pylint` (10.00/10) clean, packaging dry-runs pass,
and web mode serves `GET / → 200`.

## 1. Defects found and fixed

### F-01 — Sync import could overwrite the history database with a non-database file

- **Description.** `SyncManager` wrote a downloaded/decrypted payload straight
  over `~/.streamcatch/history.db` without validating it. Running the sync test
  suite replaced the real database with the bytes `{"remote": "config"}`.
- **Evidence anchor.** T1 — the next application start logged
  `Failed to initialize/migrate history DB: file is not a database`; the file
  contained the payload above. Fix in `sync_manager.py` (`_is_valid_history_db`,
  `_backup_existing_db`, `_replace_history_db`, `_import_history_db`).
- **Root cause.** The extraction path trusted its own archive format and treated
  "file exists" as "file is a database"; no magic-header or integrity check, no
  backup, and the replacement was not atomic.
- **Impact.** Total, silent loss of the user's download history — the most
  destructive defect found. Any malformed sync payload (corrupt cloud copy,
  partial download, wrong file selected by the user) triggers it.
- **Category.** Incremental (correctness/durability).
- **Peer reference.** `history_manager.py` validates through SQLite itself at
  init; the import path had no equivalent gate.
- **Severity.** High. **Confidence.** High (reproduced). **Effort.** ~1 h.
  **ROI.** Very high.
- **Recommendation.** Validate the SQLite magic header plus `PRAGMA
  integrity_check` in read-only mode before replacing, keep a `.bak` of the
  previous database, and refuse the import otherwise.
- **Validation.** `tests/test_additional_coverage.py::TestSyncHistoryValidation`
  (rejects garbage payloads, accepts a real database, preserves the previous DB).
- **Residual risk.** A structurally valid SQLite file that is not a StreamCatch
  history DB (e.g. another application's DB) passes the header/integrity checks;
  the schema check on replace is limited to the migration path.

### F-02 — Timer-driven queue refresh crashed before the queue was ever shown

- **Description.** `AppController._background_loop` repaints the queue view on a
  timer from startup, while the initial view is the Dashboard. Controls that had
  never been mounted called `Control.update()` unconditionally, which asserts
  `Control must be added to the page first`.
- **Evidence anchor.** T1 — reproduced against the real `main.main()` wiring and
  a real `flet.Page`: with the pre-fix unconditional update,
  `UIManager.update_queue_view()` raises in `app_layout._safe_update →
  Control.update` (`flet_core/control.py:286`); with `safe_update()` it returns
  silently and emits no commands. The scenario is permanent in
  `tests/test_startup_smoke.py::test_queue_refresh_before_the_queue_is_ever_shown_is_silent`
  (fails on the pre-fix behaviour, passes after), and the unit-level contract is
  in `tests/test_hardening_regressions.py::TestDownloadItemDetachedSafety`.
- **Mechanism, measured.** Two cases must be distinguished, and only the first
  raises: (a) *never mounted* — `control.page is None`, `update()` asserts;
  (b) *mounted, then navigated away* — Flet 0.21 keeps a **stale `page`
  reference** on the detached subtree, so `update()` does **not** raise, it just
  sends commands for controls the client no longer displays. The guard therefore
  fixes case (a) outright and leaves case (b) costing nothing in practice
  because F-11's render-signature gating means unchanged rows issue no update at
  all; only rows whose values actually changed are pushed while hidden.
  (An earlier draft of this note implied case (b) also raised; that was wrong.)
- **Root cause.** The refresh path assumed the queue was the visible view, and
  Flet's contract is that updates are only valid for mounted controls.
- **Impact.** On a fresh launch, an exception per background tick (twice per
  second) before the user ever opens the Queue, aborting the whole repaint and
  filling the log/crash reporting.
- **Category.** Incremental. **Peer reference.** `youtube_panel.apply_profile`
  already needed the same guard (it was the one pre-existing test failure).
- **Severity.** High. **Confidence.** High (reproduced end to end). **Effort.**
  ~2 h. **ROI.** High.
- **Recommendation.** One canonical `ui_utils.safe_update(control)` helper that
  checks `control.page` before updating, used by the download item, queue view,
  preview card, input card, and YouTube panel.
- **Validation.** The real-page smoke test above, `TestDownloadItemDetachedSafety`,
  `TestQueueViewRefreshWithDetachedView`,
  `TestSafeUpdateHelper::test_preview_card_update_info_works_detached` (the
  previously unexercised `update_info({})` path).
- **Residual risk.** `safe_update` swallows *all* exceptions raised by `update()`,
  including transport failures; they are logged at debug level only. Case (b)
  remains: while the queue is hidden but previously mounted, changed rows still
  push commands that the client ignores.

### F-03 — Queue keyboard shortcuts acted on a hidden view and crashed

- **Description.** `J`/`K`/`Delete` ran regardless of the visible view. On the
  Dashboard they mutated the hidden queue's selection and repainted controls that
  were not attached to the page; `ListView.scroll_to()` also issues an update on
  the list itself.
- **Evidence anchor.** T1 — `tests/test_startup_smoke.py::test_queue_keyboard_shortcuts_ignore_hidden_queue`
  drives the real handler on a real `flet.Page`; it fails when the guard in
  `main.on_keyboard` is removed and passes with it.
- **Root cause.** The handler was registered globally and only checked that the
  queue view object existed, not that it was mounted.
- **Impact.** Unhandled exception inside a keyboard event handler (same class as
  F-02) plus invisible state mutation.
- **Category.** Incremental. **Peer reference.** Other views guard their event
  handlers with `if self.page`.
- **Severity.** Medium. **Confidence.** High. **Effort.** ~1 h. **ROI.** Medium.
- **Recommendation.** Ignore queue shortcuts while `queue_view.page is None`, and
  make `select_item()` detached-safe (highlight repaints via `safe_update`,
  `scroll_to` only when mounted).
- **Validation.** The smoke test above plus
  `TestQueueKeyboardSelectionSafety` and the updated
  `tests/test_queue_view_coverage.py::test_select_item` (asserts scroll is
  skipped when detached).
- **Residual risk.** Shortcut scope is inferred from mount state rather than an
  explicit "active view" API; correct today, but a second mounted queue view
  would confuse it.

### F-04 — Localized strings were double-formatted in 7 user-visible places

- **Description.** `LocalizationManager.get(key, *args)` treats positional extras
  as **format arguments**. Call sites passed the English fallback positionally,
  so the fallback was interpolated into the template instead of being used only
  when the key is missing.
- **Evidence anchor.** T1 — measured against `locales/en.json`:

  | Key | Rendered before | Correct |
  | --- | --- | --- |
  | `stats_downloading` | `3 downloading downloading` | `3 downloading` |
  | `stats_queued` | `2 queued queued` | `2 queued` |
  | `paused_items` | `Paused Paused 4 items items` | `Paused 4 items` |
  | `cleared_items` | `Cleared Cleared 2 items items` | `Cleared 2 items` |

- **Root cause.** An API whose second positional parameter means "format value"
  was documented and used by call sites as if it meant "default".
- **Impact.** Garbled text in the queue header and in pause/resume/clear
  snackbars for every language, and no fallback at all when a key is missing.
- **Category.** Incremental (correctness of a shared API). **Peer reference.**
  `LM.get("status_scheduled_time", sched_time.strftime("%H:%M"))` is a correct
  format-argument use, which shows the ambiguity is real.
- **Severity.** Medium. **Confidence.** High. **Effort.** ~2 h. **ROI.** High.
- **Recommendation.** Add a keyword-only `default=` parameter, migrate all 59
  literal positional fallbacks to it, and enforce the convention with an AST scan.
- **Validation.** `tests/test_locale_key_usage.py::TestLocalizationGetCallSites`
  (fails if any call passes a string literal positionally) and the
  `default=` semantics test.
- **Residual risk.** Third-party code calling `LM.get` positionally keeps the old
  behaviour; today the repository is the only consumer.

### F-05 — Missing localization keys rendered as raw identifiers

- **Description.** `LM.get` falls back to English only if the key exists in
  `en.json`. Keys used in code but absent from the locale files (or from any
  loaded language) surface as `snake_case_key` in the UI.
- **Evidence anchor.** T1 — the parity tests only compared en/es/fa, so a key
  missing from *all three* passed them; `tests/test_locale_key_usage.py` now scans
  every `LM.get("literal")` reference against the English reference file.
- **Root cause.** No test tied code usage to locale contents.
- **Impact.** Untranslated, machine-looking labels reach users; the failure is
  invisible in CI.
- **Category.** Incremental. **Peer reference.** Parity tests already existed and
  were necessary but not sufficient.
- **Severity.** Low–Medium. **Confidence.** High. **Effort.** ~1 h. **ROI.** Medium.
- **Recommendation.** Keep the usage scan, add the missing keys to all locales.
- **Validation.** `tests/test_locale_key_usage.py` (3 tests: usage exists, parity
  holds, JSON is well-formed); 4 missing keys were added during this pass.
- **Residual risk.** Dynamically composed keys (`f"language_name_{code}"`) would
  be missed by the literal scan; none exist in the current tree.

### F-06 — History size statistics were a hard-coded placeholder

- **Description.** `HistoryManager.get_stats()` returned `total_size_mb: 0`
  unconditionally with a comment saying accurate statistics "should be stored in
  future", and nothing consumed the method.
- **Evidence anchor.** T2 anchor `history_manager.py::get_stats` (pre-change);
  T1 after the change — `TestHistoryStats` sums mixed storage shapes
  (`"12.50 MB"`, raw byte counts, `"N/A"`) to `13.5 MB` for three entries.
- **Root cause.** `file_size` has been written in two shapes over the project's
  life (raw bytes from the engines, pre-formatted strings from
  `format_file_size`), so aggregation was deferred.
- **Impact.** Dead API with a false value; a dashboard/history summary that
  reports 0 bytes for non-empty history.
- **Category.** Incremental. **Peer reference.** `get_download_activity()`
  already aggregates in SQL with a `typeof()` guard — a similar tolerance was
  needed here.
- **Severity.** Low. **Confidence.** High. **Effort.** ~2 h. **ROI.** Medium.
- **Recommendation.** Parse both shapes tolerantly (`_parse_size_bytes`), sum in
  Python, and surface the result in the history view as a totals line so the API
  has a real consumer.
- **Validation.** `TestHistoryStats` (10 parameterized parsing cases + mixed
  aggregation + empty history), `TestHistorySummaryLine` (renders, hides when
  empty, survives a broken stats source).
- **Residual risk.** Unknown-unit strings (for example a bare `"500"` from a
  legacy build) are read as bytes; the parser is intentionally forgiving.

### F-07 — Proxy validation accepted loopback and private targets

- **Description.** `DownloadOptions` validated that a proxy string had a host and
  port but allowed `127.0.0.1`, RFC1918 addresses, multicast, and reserved
  ranges, unlike every other outbound-URL path in the project.
- **Evidence anchor.** T2 anchor `downloader/types.py::_validate_proxy_host`;
  T1 — `TestProxyValidation` (rejects loopback/private/multicast/reserved/
  unspecified, malformed dotted-quads, and out-of-range ports; accepts public
  hosts with optional credentials).
- **Root cause.** URL safety checks (`ui_utils._host_is_public`) were never
  applied to the proxy field, which is also attacker-influencable configuration.
- **Impact.** A crafted proxy setting can redirect the downloader's traffic to
  local services (SSRF-style), and the setting persists across runs.
- **Category.** Incremental (hardening). **Peer reference.**
  `ui_utils._host_is_public` performs exactly this check for URLs.
- **Severity.** Medium. **Confidence.** Medium-High (path traced; no exploit
  chain demonstrated beyond configuration-driven redirection). **Effort.** ~2 h.
  **ROI.** Medium.
- **Recommendation.** Reject non-public hosts and malformed addresses, keep the
  message actionable.
- **Validation.** `TestProxyValidation`, `test_download_options_rejects_bad_proxy`,
  `test_download_options_accepts_public_proxy`.
- **Residual risk.** A user with a legitimate LAN proxy can no longer configure it;
  this matches the project's existing policy for URLs, but is a real behaviour
  change for that (uncommon) setup.

### F-08 — Download-path policy blocked legitimate destinations

- **Description.** `ui_utils.is_safe_path` allowed only paths under the user's
  home directory. Downloads to `/tmp`, removable media, or any other writable
  volume were rejected.
- **Evidence anchor.** T2 anchor `ui_utils.py::is_safe_path`; T1 —
  `TestImportPathPolicy` (home allowed, temp allowed, `/etc`, `/proc`, `/var`,
  `/boot`, `/root`, `C:\Windows` denied).
- **Root cause.** The original implementation inverted the problem: it tried to
  allow-list one safe root instead of denying system locations.
- **Impact.** Legitimate desktop flows (download to an external drive, temp
  workspace) failed with a security error.
- **Category.** Incremental. **Peer reference.** Desktop file-chooser defaults.
- **Severity.** Medium (usability). **Confidence.** High. **Effort.** ~1.5 h.
  **ROI.** Medium.
- **Recommendation.** Deny-list system directories, keep the checks tolerant of
  non-existent paths, and normalise before comparison.
- **Validation.** `TestImportPathPolicy`, plus the pre-existing
  `tests/test_ui_utils.py` / `test_ui_utils_extended.py` suites.
- **Residual risk.** The deny-list is a fixed list; a distribution with an
  unusual system layout could fall outside it. Symbolic links are resolved before
  the check, so a link into a denied directory is still rejected.

### F-09 — Worker pool was torn down by reconfiguration

- **Description.** `configure_concurrency()` shut the shared
  `ThreadPoolExecutor` down and rebuilt it, while `process_queue` iterated a
  global that could change mid-flight. A `break` inside `finally` also aborted
  the worker loop, and a claimed item was lost if the job could not be submitted.
- **Evidence anchor.** T2 anchors `tasks.py::_get_semaphore`,
  `tasks.py::configure_concurrency`, `tasks.py::process_queue`; T1 —
  `TestConcurrencyReconfiguration` (single long-lived executor, the running job
  releases its own semaphore).
- **Root cause.** Concurrency was treated as immutable while the settings UI
  exposes it at runtime; the executor was the de-facto owner of the semaphore.
- **Impact.** Silent loss of queued work and possible thread leaks when the user
  changes the concurrency setting; a claimed item could vanish from the queue.
- **Category.** Incremental (reliability). **Peer reference.** The queue manager
  already owns hand-off state transitions; the executor is not the right place
  for the semaphore.
- **Severity.** Medium. **Confidence.** High (code path traced + tests). **Effort.**
  ~3 h. **ROI.** Medium-High.
- **Recommendation.** One long-lived executor with a swappable submission
  throttle guarded by a lock; workers capture the semaphore locally; return a
  claimed item to the queue when submission fails.
- **Validation.** `TestConcurrencyReconfiguration` and the existing
  `tests/test_final_tasks.py`, `tests/test_pipeline_integration.py`.
- **Residual risk.** The throttle swap is only partially synchronised with
  in-flight submissions; a job admitted during a shrink may briefly exceed the new
  limit.

### F-10 — Queue lookups were linear inside the lock

- **Description.** `get_item_by_id`, `update_item_status`, `remove_item`,
  `cancel_item`, `retry_item`, and `clear_completed` scanned the list while
  holding the queue lock.
- **Evidence anchor.** T2 anchors in `queue_manager.py`; T1 —
  `TestQueueIndexConsistency` including a six-thread stress test and a
  high-frequency update test.
- **Root cause.** The queue is a list (ordering matters) and the id lookup was
  bolted onto it rather than indexed beside it.
- **Impact.** ~0.5 s repaint cadence over a queue of hundreds of items with
  status updates arriving from every worker; contention grows with the queue,
  which is exactly when the UI is already busy.
- **Category.** Incremental (performance). **Peer reference.** `_index` dict
  beside the ordered list is the standard pattern.
- **Severity.** Medium. **Confidence.** Medium-High (complexity reasoning plus
  stress test; no end-to-end profile was captured). **Effort.** ~3 h. **ROI.**
  Medium.
- **Recommendation.** Maintain a self-healing id→item index next to the list and
  keep both in sync in every mutation, normalising ids to `str`.
- **Validation.** `TestQueueIndexConsistency` (add/remove, clear, cancel/retry,
  unknown ids, 6-thread stress, high-frequency updates).
- **Residual risk.** Two structures must stay consistent; the self-healing
  fallback hides a divergence instead of failing loudly.

### F-11 — Queue refresh repainted every row on every tick

- **Description.** Each timer tick re-rendered every queue row, sending one Flet
  update command per item per tick, even when nothing had changed.
- **Evidence anchor.** T1 — a throwaway harness with 200 parked items measured
  **0 `Control.update()` calls while nothing changed and exactly 1 when a single
  item's progress changed**; `TestDownloadItemRepaintGating` and
  `TestQueueViewRefreshWithDetachedView` now encode that contract permanently.
  `QueueView.rebuild()` over 400 items completed in ~18 ms unmounted.
- **Root cause.** `update_state()` unconditionally recomputed and pushed the row.
- **Impact.** Thousands of pointless WebSocket commands per minute on an idle
  queue with hundreds of finished items; CPU and battery cost on the client.
- **Category.** Incremental (performance). **Peer reference.** Diff logic already
  existed for structure; only the leaf repaint was missing.
- **Severity.** Medium. **Confidence.** High (measured). **Effort.** ~2 h. **ROI.**
  High.
- **Recommendation.** Gate the repaint on a render signature (status, progress,
  speed, ETA, size, title, schedule, error); reuse the existing controls.
- **Validation.** The three tests named above; a mutation of the live item dict
  in place is still detected.
- **Residual risk.** The signature must be extended whenever a new visible field
  is added, or that field will render stale.

### F-12 — History search issued one SQL query per keystroke

- **Description.** `on_change` on the history search field triggered an
  `LIKE '%term%'` query (an index cannot serve a leading wildcard) on every
  keystroke.
- **Evidence anchor.** T2 anchor `views/history_view.py::_search_timer`
  (debounce, 350 ms) and `_apply_search_from_timer`.
- **Root cause.** Live search was wired directly to the data loader.
- **Impact.** UI jank and needless database load while typing.
- **Category.** Incremental (performance/UX). **Peer reference.** Queue search
  filters in memory, so no debounce is needed there.
- **Severity.** Low. **Confidence.** High. **Effort.** ~1 h. **ROI.** Medium.
- **Recommendation.** Debounce the query and cancel a pending timer before
  scheduling a new one.
- **Validation.** `tests/test_history_view_coverage.py` and
  `tests/test_final_history_view.py` cover load/search behaviour.
- **Residual risk.** A pending timer that fires after the view is detached relies
  on the fallback load path; covered by the `self.page is None` branch.

### F-13 — Reconfiguration and environment defects in web/Docker mode

- **Description.** Web mode bound the Flet server to loopback, so the container
  port mapping could not reach it; `docker-compose.yml` did not set
  `FLET_SERVER_HOST`; the high-contrast theme mode resolved to `SYSTEM`, ignoring
  the user's choice.
- **Evidence anchor.** T1 — `Uvicorn running on http://0.0.0.0:<port>` and
  `GET / HTTP/1.1 200 OK` from the live preview; `docker-compose.yml` and
  `Dockerfile` now pass `FLET_SERVER_HOST=0.0.0.0`.
- **Root cause.** Desktop and web entry points shared defaults written for
  loopback-only local runs.
- **Impact.** The documented Docker path served nothing; the high-contrast mode
  silently rendered as system theme.
- **Category.** Incremental (deployment/UX). **Peer reference.** Flet's own web
  server defaults to loopback for safety; containers must override.
- **Severity.** Medium. **Confidence.** High. **Effort.** ~1 h. **ROI.** Medium.
- **Recommendation.** Bind `0.0.0.0` in web mode (still configurable via
  `FLET_SERVER_HOST`), log host/port, and resolve the theme mode explicitly.
- **Validation.** Live web preview plus `tests/test_startup_smoke.py` and
  `TestThemePalettes`.
- **Residual risk.** Binding all interfaces exposes the UI to the local network;
  acceptable for the documented container use, and the host remains configurable.

### F-14 — Dashboard health chips measured the wrong volume

- **Description.** The storage and health chips reported the home-directory
  volume rather than the configured download path.
- **Evidence anchor.** T2 anchor `views/dashboard_view.py` (uses
  `get_default_download_path(state.config.get("download_path"))`).
- **Root cause.** The download path setting was added after the chips were.
- **Impact.** Free-space figures mislead users who download to another drive.
- **Category.** Incremental. **Peer reference.** `SettingsView` already resolves
  the same path for validation.
- **Severity.** Low. **Confidence.** High. **Effort.** ~30 min. **ROI.** Medium.
- **Recommendation.** Resolve the configured path before measuring.
- **Validation.** `tests/test_dashboard_health.py`.
- **Residual risk.** A configured path that does not exist falls back to the home
  directory; the chip does not say which volume it measured.

### F-15 — Batch import rejected CSV/TXT and read unbounded files

- **Description.** Only a narrow set of extensions was accepted, and file size
  was only checked after reading the whole file into memory.
- **Evidence anchor.** T2 anchor `batch_importer.py` (extension check, then a
  5 MB cap via `int(path.stat().st_size)` before reading); T1 —
  `TestBatchImporterCsv` (CSV accepted, quoted fields parsed, oversized file
  rejected without reading, unsupported extension rejected).
- **Root cause.** Input validation was added incrementally per format.
- **Impact.** A large file could stall startup or exhaust memory; a plain URL list
  (`.txt`) could not be imported at all.
- **Category.** Incremental. **Peer reference.** `ui_utils` size helpers.
- **Severity.** Low–Medium. **Confidence.** High. **Effort.** ~2 h. **ROI.** Medium.
- **Recommendation.** Accept `.csv`/`.txt`, enforce the cap before reading, and
  keep the tolerant `stat` handling for mocks.
- **Validation.** `TestBatchImporterCsv`.
- **Residual risk.** The cap is a fixed 5 MB; a legitimate 100k-URL list is
  rejected with a clear error rather than streamed.

### F-16 — Extractor support cache was unbounded; playlist failures were hidden

- **Description.** `yt_dlp.supports()` cached every probed URL forever, and
  playlist runs set `ignoreerrors = True` with no reporting of partial failures.
- **Evidence anchor.** T2 anchors `downloader/engines/ytdlp.py::_SUPPORT_CACHE`
  (LRU, max 500) and the playlist result (`entries` + `failed_entries`); T1 —
  `TestYTDLPSupportCache` (cache is bounded, empty URL unsupported).
- **Root cause.** A memoization decision made without a bound, and error
  suppression chosen for playlist robustness without surfacing counts.
- **Impact.** Unbounded memory growth in long sessions; the UI reported a
  successful playlist run even when most entries failed.
- **Category.** Incremental. **Peer reference.** `ignoreerrors` is now applied
  only for playlists.
- **Severity.** Low–Medium. **Confidence.** Medium-High. **Effort.** ~2 h. **ROI.**
  Medium.
- **Recommendation.** Bound the cache, keep the safe default (`True` when
  unknown), and report both successes and failures.
- **Validation.** `TestYTDLPSupportCache`, `TestDownloadJobStatusMapping`.
- **Residual risk.** The `failed_entries` contract is new; the UI consumes it as
  optional data, so older callers remain compatible.

### F-17 — Accumulated repository hygiene issues

- **Description.** `.venv/` was not ignored; `isort` walked it; a generated
  rotated log (`ytdownloader.log.1`, 5 MB) was swept into a commit by
  `git add -A` in this session.
- **Evidence anchor.** T1 — `git rm --cached ytdownloader.log.1` plus
  `ytdownloader.log.*` in `.gitignore`, verified by a clean `git status`.
- **Root cause.** Ignore rules lagged behind the tooling introduced by this
  session.
- **Impact.** Accidental commits of generated content; slow lint runs.
- **Category.** Incremental (maintainability). **Peer reference.** `.gitignore`
  already covered `ytdownloader.log` but not its rotated sibling.
- **Severity.** Low. **Confidence.** High. **Effort.** ~15 min. **ROI.** Medium.
- **Recommendation.** Ignore build environments and rotated logs; keep generated
  artifacts out of version control (the file remains on disk).
- **Validation.** `git status --short` is empty after the change.
- **Residual risk.** The blob remains in the branch history; removing it would
  require rewriting published history.

## 2. User-facing improvements

| Improvement | Anchor | Evidence |
| --- | --- | --- |
| Live theme switching (dark/light/high-contrast) without restart | `theme.py`, `ui_manager.refresh_theme` | `TestThemePalettes`, `TestThemeRefreshPropagation`, smoke test on a real page |
| Queue search + status filter, distinct "no results" empty state, bulk actions unaffected by filters | `views/queue_view.py` | `tests/test_queue_filtering.py` (15 tests) |
| Live queue progress (timer repaint, faster while downloading) | `app_controller._background_loop` | `TestQueueViewRefreshWithDetachedView` |
| History totals line (count + on-disk size) | `views/history_view.py::_update_summary` | `TestHistorySummaryLine` |
| Debounced history search | `views/history_view.py` | history view suites |
| Dashboard chips measure the configured download volume | `views/dashboard_view.py` | `tests/test_dashboard_health.py` |
| RSS add/duplicate feedback | `views/rss_view.py` | `tests/test_rss_manager.py`, locale keys |
| Batch import of `.csv`/`.txt` with a size cap | `batch_importer.py` | `TestBatchImporterCsv` |
| Actionable tooltips and localized filters | `locales/{en,es,fa}.json` | `test_locale_key_usage.py` |
| History backup and restore (Export/Import History buttons, idempotent, timestamps preserved) | `views/history_view.py`, `HistoryManager.import_entries`/`import_from_json_file`, `AppController.on_export_history` | `TestHistoryImportExport`, `TestHistoryBackupControllerFlow`, end-to-end run on a real page |
| Spanish/Persian translations for 48 strings that were still English | `locales/{es,fa}.json` | `TestTranslationsAreComplete` |
| Relocatable user-data directory (`STREAMCATCH_DATA_DIR`) | `app_paths.py` | `TestAppDataDirectory` |

## 3. Verification performed

```
pytest -q                                  512 passed
pytest -q --cov=. --cov-report=term-missing 78% statements (floor 60%)
black --check .                            clean (104 files)
isort --check-only .                       clean
ruff check . --exclude tests               All checks passed
mypy --config-file mypy.ini .              no issues in 34 source files
pylint <non-test sources>                  10.00/10
python scripts/build_installer.py --dry-run --skip-installer   resolved commands printed
python scripts/build_mobile.py --target apk --dry-run          resolved commands printed
FLET_WEB=1 FLET_SERVER_PORT=8550 python main.py                serves GET / -> 200
```

Regression discipline: the detached-control, repaint-gating, keyboard-gate,
localization, and size-aggregation tests were each run against the pre-change
implementation and failed there (for example 7 of 11 new update-safety tests fail
without `safe_update`, and the keyboard smoke test fails when the mount guard is
removed).

## 4. Coverage ledger

Reviewed end to end (T1/T2): `main.py`, `app_controller.py`, `app_state.py`,
`app_layout.py`, `ui_manager.py`, `theme.py`, `ui_utils.py`, `tasks.py`,
`queue_manager.py`, `history_manager.py`, `config_manager.py`,
`batch_importer.py`, `sync_manager.py`, `cloud_manager.py`, `rss_manager.py`,
`social_manager.py`, `clipboard_monitor.py`, `download_scheduler.py`,
`rate_limiter.py`, `localization_manager.py`, `logger_config.py`, `utils.py`,
`downloader/*` (core, info, types, constants, engines, extractors),
`views/*` and `views/components/*`, `scripts/build_*.py`, `Dockerfile`,
`docker-compose.yml`, `.github/workflows/*`, `requirements*.txt`, `pyproject.toml`,
`mypy.ini`, `installers/setup.iss`, `README.md`, `PROJECT_HEALTH.md`, `wiki/*`.

Coverage of the corpus: 22 of 22 top-level modules, 5 of 5 downloader modules,
16 of 16 view/component/panel modules, 5 of 5 CI workflows. Files not reviewed line by line:
`assets/*` (static images/icon), `CODE_OF_CONDUCT.md`, `LICENSE`,
`ytdownloader.log.1` (generated), `installers/setup.iss` (reviewed only for the
packaging claims it must support). No file in the repository was skipped without a
reason recorded here.

Lowest-coverage areas after the pass (T1, from the coverage report):
`main.py` 48% (startup and crash paths), `views/download_view.py` 45%,
`views/components/panels/instagram_panel.py` 48%,
`views/components/download_input_card.py` 58%, `ui_utils.py` 65%,
`downloader/engines/ytdlp.py` 66%, `downloader/core.py` 67%,
`rss_manager.py` 62%.

## 5. Deferred items and residual risk

Deferred deliberately, with the reason:

1. **Write-only state fields** — `AppState.is_paused`, `.current_download_item`,
   `.cinema_mode` are assigned but never read (verification: repository-wide grep
   finds no reader outside `app_state.py`). Removing them changes an attribute
   surface other code may use; wiring them invents features. Left as a product
   decision, documented here.
2. **14 unreferenced locale keys** — `export_settings`, `import_settings`,
   `settings_exported`, `settings_imported`,
   `select_all`/`deselect_all`/`delete_selected`/`confirm_delete`, and
   `language_name_*` (verification: literal scan over non-test sources; the four
   history keys that were on this list are now used by the delivered
   export/import feature). They cost nothing and hint at unfinished work:
   settings export/import and multi-select delete have no implementation at all.
   The `language_name_*` keys are unused because the language dropdown shows
   endonyms ("English", "Español", "فارسی") on purpose — that is the better UX
   and should stay even if the keys are eventually dropped. Adding UI for the
   remaining keys is a product decision, not a bug fix.
3. **Redundant `if tb:` inside `if stack:` in `global_crash_handler`** —
   `traceback.extract_tb(None)` yields an empty list, so the outer guard already
   implies `tb` is set. Harmless; left untouched to avoid churn in the crash path.
4. **`main.py` at 48% statement coverage** — the startup chart and the Windows
   message-box branch are hard to exercise headlessly; the smoke tests cover the
   mounted-tree path. A real Windows run remains a manual check.
5. **Redaction is name-based** — crash-log locals are redacted when the variable
   name matches key/token/password/secret/auth. A secret held in a local named
   `cfg` or `value` would be written to the log. Verified by the new test
   (`TestCrashHandlerRedaction`), which also asserts the log is created `0600`.
   Content-based redaction was rejected as unpredictable.
6. **Web-mode parity for desktop-only flows** — file pickers, `open folder`,
   and FFmpeg detection were not validated against a real browser session; only
   the server bind and initial render were verified.
7. **No end-to-end profile of a real download** — performance claims are from
   unit-level measurements (repaint counts, rebuild timing), not a live multi-GB
   download on a real network. Real yt-dlp and Windows installer runs remain
   manual checks in `PROJECT_HEALTH.md`.
8. **Concurrency throttle shrink race** — see F-09 residual risk.

## 6. Compatibility notes

- No public API was removed. `LocalizationManager.get` gained a keyword-only
  parameter; `HistoryManager.get_stats` gained a value where it previously
  returned a placeholder; `ui_utils` gained `safe_update`.
- CI workflows, packaging scripts, the Docker build, and the locale file set are
  unchanged in contract (docs updated to match the code).
- Desktop-first behaviour is preserved; the tool remains a Flet + yt-dlp desktop
  downloader, and no subsystem was deleted.
### F-18 — Test runs wrote to the developer's real user data

- **Description.** `ConfigManager.CONFIG_FILE` and `HistoryManager.DB_FILE` were
  hard-coded under `$HOME/.streamcatch`. Any test that constructed a real
  `HistoryManager` or saved configuration mutated the developer's actual
  history database, configuration, and log file.
- **Evidence anchor.** T1 — counted before/after a full suite run:
  `history.db` **29 → 33 rows** per run, the 1.9 MB `app.log` grew on every run,
  and `config.json` was rewritten (all three mtimes updated by the run).
- **Root cause.** The data directory was a constant, so tests had no way to
  redirect it; individual tests could only opt out one instance at a time.
- **Impact.** Running tests contaminates real user state; a test calling
  `clear_history()` would **delete the developer's history**, and a config test
  could overwrite real settings. It also hid the `clear_history` risk from
  review because the damage happens outside the test assertion.
- **Category.** Incremental (correctness/test isolation). **Peer reference.**
  `HistoryManager._test_db_file` already existed as a per-instance escape hatch,
  which is exactly the fragile pattern that let this persist.
- **Severity.** Medium-High. **Confidence.** High (measured, reproducible).
  **Effort.** ~1.5 h. **ROI.** High.
- **Recommendation.** One canonical `app_paths.data_dir()`/`data_file()` helper
  driven by `STREAMCATCH_DATA_DIR`, used by config, history, the logger, and the
  sync fallback; `tests/conftest.py` points it at a temporary folder before any
  application import.
- **Validation.** `TestAppDataDirectory` (env override, blank fallback, tilde
  expansion, all three files inside the data dir) plus a session guard test that
  fails if the suite is ever pointed at the real profile; before/after row counts
  and file sizes unchanged across a full run.
- **Residual risk.** Modules resolve their path at import, so the variable must
  be set before startup; changing it at runtime does not move existing files
  (documented in `app_paths` and `wiki/API.md`).

### F-19 — Invented Flet icon name would fail at render time

- **Description.** A new import button referenced
  `ft.icons.DOWNLOAD_FILE_ROUNDED`, which does not exist in Flet 0.21.2 (the
  correct name is `FILE_DOWNLOAD_ROUNDED`).
- **Evidence anchor.** T1 — `AttributeError: module 'flet_core.icons' has no
  attribute 'DOWNLOAD_FILE_ROUNDED'` from the real-Flet tests; a scan of all 74
  distinct `ft.icons.*`/`ft.colors.*` references in the repository found this as
  the only invalid name.
- **Root cause.** Every mock-based test accepts any attribute
  (`ft.icons.<anything>` returns a `MagicMock`), so invalid enum names pass
  every mocked test and only fail in the running app.
- **Impact.** The History view would raise while building its header, breaking
  the whole screen — and the class of bug is invisible to the default test mode.
- **Category.** Incremental. **Peer reference.** `tests/test_startup_smoke.py`
  already runs against real Flet, which is why it caught this immediately.
- **Severity.** Medium. **Confidence.** High. **Effort.** ~1 h. **ROI.** High.
- **Recommendation.** Use `FILE_DOWNLOAD_ROUNDED`, and keep a permanent scan
  that validates every literal `ft.icons.*`/`ft.colors.*` reference against the
  installed Flet.
- **Validation.** `tests/test_startup_smoke.py::test_icon_and_colour_names_exist_in_real_flet`
  (fails on an unknown name, and on a scan that stops finding references).
- **Residual risk.** The scan only covers literal attribute access; names built
  dynamically (for example `getattr(ft.icons, name)`) are not checked.

