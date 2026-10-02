# Roadmap

## Current Focus (Near Term)

### Stability and Quality

- Keep full regression suite green across supported Python versions.
- Continue hardening queue/threading paths under heavy load.
- Expand integration coverage for packaging and release scripts.

### Platform Delivery

- Improve reproducibility of native desktop builds.
- Maintain Android APK release automation.
- Improve signed/distribution-ready metadata for platform stores.

### UX and Operability

- Add richer queue filtering/sorting. *(Status filter + title/URL search shipped;
  custom sort orders are still open.)*
- Add clearer error surfaces and recovery actions in UI.
- Improve observability around long-running downloads and sync tasks.

## Mid Term

- Multi-provider cloud sync abstraction beyond Google Drive.
- Smarter queue presets/profiles for recurring download workflows.
- Optional plugin surface for source-specific behaviors.

## Long Term

- First-party browser companion for one-click queueing.
- More advanced media postprocessing presets.
- Device-to-device session portability improvements.

## Recently Completed

- Queue pause-all/resume-all controls.
- Dashboard system health chips and richer stats.
- Improved high-contrast persistence + theme consistency.
- Hardened mobile build script with artifact verification.
- Wiki/documentation refresh with end-to-end EXE/APK guidance.
- Full dark/light/high-contrast palettes with live theme switching (views are
  rebuilt so the change is visible immediately).
- O(1) queue item index; progress updates no longer scan the whole queue.
- Runtime-safe concurrency changes: one long-lived worker pool plus a swappable
  semaphore, so changing `max_concurrent_downloads` never orphans downloads.
- CSV batch import alongside plain-text lists, with size and count caps.
- Docker/web mode now binds `0.0.0.0` so published container ports work.
- Lint/type gates are green: black, isort, ruff, pylint (10.00/10) and mypy all
  pass on the non-test sources; 416 tests at 75% coverage.
