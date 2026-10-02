"""
Regression tests for the hardening / redesign pass.

Each test here is written to fail against the previous implementation and pass
against the corrected behaviour. Grouped by subsystem for easy triage.
"""

import csv
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from downloader.types import DownloadOptions, DownloadStatus
from localization_manager import LocalizationManager as LM
from queue_manager import QueueManager

# ---------------------------------------------------------------------------
# Queue manager: O(1) id index must stay consistent with the ordered list
# ---------------------------------------------------------------------------


class TestQueueIndexConsistency:
    def _make_item(self, url="https://example.com/v.mp4", **extra):
        item = {"url": url, "status": "Queued", "title": f"T-{url[-6:]}"}
        item.update(extra)
        return item

    def test_index_tracks_add_and_remove(self):
        qm = QueueManager()
        qm.add_item(self._make_item("https://example.com/a.mp4"))
        qm.add_item(self._make_item("https://example.com/b.mp4"))

        assert qm.get_queue_count() == 2
        assert len(qm._index) == 2

        first = qm.get_all()[0]
        qm.remove_item(first)

        assert qm.get_queue_count() == 1
        assert len(qm._index) == 1
        assert qm.get_item_by_id(first["id"]) is None
        # The surviving item must still be addressable
        survivor = qm.get_all()[0]
        assert qm.get_item_by_id(survivor["id"]) is not None

    def test_index_updates_after_clear_completed(self):
        qm = QueueManager()
        for i in range(3):
            item = self._make_item(f"https://example.com/c{i}.mp4")
            qm.add_item(item)
            qm.update_item_status(item["id"], DownloadStatus.COMPLETED)

        assert len(qm._index) == 3
        removed = qm.clear_completed()

        assert removed == 3
        assert qm.get_queue_count() == 0
        assert qm._index == {}

    def test_index_survives_cancel_and_retry(self):
        qm = QueueManager()
        item = self._make_item()
        qm.add_item(item)
        item_id = item["id"]

        qm.cancel_item(item_id)
        assert qm.get_item_by_id(item_id)["status"] == DownloadStatus.CANCELLED

        assert qm.retry_item(item_id) is True
        assert qm.get_item_by_id(item_id)["status"] == "Queued"

    def test_retry_unknown_id_returns_false(self):
        qm = QueueManager()
        assert qm.retry_item("does-not-exist") is False

    def test_update_item_status_missing_id_is_noop(self):
        qm = QueueManager()
        qm.add_item(self._make_item())
        # Must not raise and must not corrupt state
        qm.update_item_status("missing", DownloadStatus.ERROR)
        assert qm.get_statistics()["total"] == 1

    def test_high_frequency_updates_are_consistent(self):
        """Hammer progress updates from several threads; index must stay valid."""
        qm = QueueManager()
        ids = []
        for i in range(20):
            item = self._make_item(f"https://example.com/t{i}.mp4")
            qm.add_item(item)
            ids.append(item["id"])

        errors: list[BaseException] = []

        def worker(worker_id: int):
            try:
                for tick in range(50):
                    item_id = ids[(worker_id + tick) % len(ids)]
                    qm.update_item_status(
                        item_id,
                        DownloadStatus.DOWNLOADING,
                        {"progress": tick / 50.0},
                    )
            except BaseException as exc:  # pragma: no cover - failure path
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert errors == []
        assert qm.get_queue_count() == 20
        assert len(qm._index) == 20
        # Every id must resolve to the object that is actually in the queue
        queue_objects = {id(entry) for entry in qm.get_all()}
        for item_id in ids:
            assert qm.get_item_by_id(item_id) is not None
        assert all(id(entry) in queue_objects for entry in qm._index.values())


# ---------------------------------------------------------------------------
# Concurrency configuration must not orphan in-flight work
# ---------------------------------------------------------------------------


class TestConcurrencyReconfiguration:
    def test_reconfigure_keeps_single_executor(self, monkeypatch):
        import tasks

        monkeypatch.setattr(tasks, "_executor", None)
        first = tasks._get_executor()
        assert tasks._get_executor() is first

        assert tasks.configure_concurrency(5) is True
        # Executor is long-lived: same object, no thread churn
        assert tasks._get_executor() is first
        assert (
            tasks._get_semaphore()._value == 5
        )  # noqa: SLF001 - introspection on purpose
        assert tasks.configure_concurrency(0) is False
        assert tasks.configure_concurrency(-3) is False

    def test_running_job_releases_its_own_semaphore(self, monkeypatch):
        """A job holding the old semaphore must release the old one, not the new."""
        import tasks

        monkeypatch.setattr(tasks, "_executor", None)
        old_sem = tasks._get_semaphore()
        assert old_sem.acquire(blocking=False) is True

        tasks.configure_concurrency(7)
        new_sem = tasks._get_semaphore()
        assert new_sem is not old_sem

        # New submissions can proceed while the old job is still running
        assert new_sem.acquire(blocking=False) is True
        new_sem.release()
        # And the old job's release does not corrupt the new semaphore
        old_sem.release()
        assert new_sem._value == 7  # noqa: SLF001 - introspection on purpose


# ---------------------------------------------------------------------------
# Theme: dual palette switching
# ---------------------------------------------------------------------------


class TestThemePalettes:
    def test_apply_theme_mode_switches_active_colors(self):
        from theme import Theme

        original = Theme.is_dark
        try:
            Theme.apply_theme_mode("dark")
            dark_bg = Theme.BG_DARK
            dark_text = Theme.TEXT_PRIMARY
            assert Theme.is_dark is True

            Theme.apply_theme_mode("light")
            assert Theme.is_dark is False
            assert Theme.BG_DARK != dark_bg
            assert Theme.TEXT_PRIMARY != dark_text
            # Nested proxies must follow the swap (legacy call sites)
            assert Theme.Text.PRIMARY == Theme.TEXT_PRIMARY
            assert Theme.Primary.MAIN == Theme.PRIMARY
            assert Theme.Divider.COLOR == Theme.DIVIDER
            assert Theme.Surface.CARD == Theme.BG_CARD
        finally:
            Theme.apply_theme_mode("dark" if original else "light")

    def test_card_decoration_uses_active_palette(self):
        from theme import Theme

        try:
            Theme.apply_theme_mode("light")
            assert Theme.get_card_decoration()["bgcolor"] == Theme.BG_CARD
            assert Theme.get_input_decoration()["bgcolor"] == Theme.BG_INPUT
        finally:
            Theme.apply_theme_mode("dark")

    def test_high_contrast_mode_keeps_dark_palette(self):
        from theme import Theme

        try:
            Theme.apply_theme_mode("high_contrast")
            assert Theme.is_dark is True
            assert Theme.get_high_contrast_theme() is not None
        finally:
            Theme.apply_theme_mode("dark")


# ---------------------------------------------------------------------------
# Theme switching must rebuild the view tree (colors are captured at build time)
# ---------------------------------------------------------------------------


class TestThemeRefreshPropagation:
    def test_refresh_theme_rebuilds_layout_on_page(self):
        from ui_manager import UIManager

        page = MagicMock()
        page.overlay = []
        page.controls = []
        page.window_width = 1400
        page.window_height = 900
        page.platform = None

        manager = UIManager(page)
        callbacks = {
            name: MagicMock()
            for name in (
                "on_fetch_info_callback",
                "on_add_to_queue_callback",
                "on_batch_import_callback",
                "on_schedule_callback",
                "on_cancel_item_callback",
                "on_remove_item_callback",
                "on_reorder_item_callback",
                "on_retry_item_callback",
                "on_toggle_clipboard_callback",
                "on_play_callback",
                "on_open_folder_callback",
            )
        }

        layout_factory = MagicMock(side_effect=[MagicMock(), MagicMock()])
        with patch.multiple(
            "ui_manager",
            DashboardView=MagicMock(),
            DownloadView=MagicMock(),
            QueueView=MagicMock(),
            HistoryView=MagicMock(),
            RSSView=MagicMock(),
            SettingsView=MagicMock(),
            AppLayout=layout_factory,
        ):
            first_layout = manager.initialize_views(**callbacks)
            assert first_layout is not None
            page.controls = [first_layout]

            manager.refresh_theme()

        # A brand new layout object must be built and mounted, otherwise the
        # palette change would not be visible.
        assert layout_factory.call_count == 2
        assert page.controls == [manager.app_layout]

    def test_refresh_theme_is_noop_before_initialization(self):
        from ui_manager import UIManager

        page = MagicMock()
        manager = UIManager(page)
        manager.refresh_theme()  # must not raise
        assert manager.app_layout is None

    def test_settings_view_forwards_theme_changes(self):
        from views.settings_view import SettingsView

        config = {"theme_mode": "Dark", "high_contrast": False}
        callback = MagicMock()
        view = SettingsView(config, on_theme_change=callback)
        view.theme_mode_dd.value = "Light"

        with patch.object(SettingsView, "page", create=True) as page_mock:
            page_mock.theme = None
            page_mock.bgcolor = None
            page_mock.update = MagicMock()
            with patch("views.settings_view.ConfigManager.save_config"):
                view._on_theme_change(None)

        assert callback.called
        assert config["theme_mode"] == "Light"


# ---------------------------------------------------------------------------
# Batch importer: CSV support promised by the file picker
# ---------------------------------------------------------------------------


class TestBatchImporterCsv:
    def _write(self, tmp_path: Path, name: str, content: str) -> Path:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_csv_files_are_accepted(self, tmp_path):
        from batch_importer import BatchImporter

        queue = MagicMock()
        queue.get_queue_count.return_value = 0
        queue.MAX_QUEUE_SIZE = 1000
        importer = BatchImporter(queue, {})

        path = self._write(
            tmp_path,
            "links.csv",
            "url,note\nhttps://example.com/1.mp4,first\nhttps://example.com/2.mp4,second\n",
        )

        with patch.object(importer, "verify_url", return_value=True):
            count, truncated = importer.import_from_file(str(path))

        assert count == 2
        assert truncated is False

    def test_csv_with_quoted_fields(self, tmp_path):
        from batch_importer import BatchImporter

        queue = MagicMock()
        queue.get_queue_count.return_value = 0
        queue.MAX_QUEUE_SIZE = 1000
        importer = BatchImporter(queue, {})

        path = tmp_path / "quoted.csv"
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["https://example.com/1.mp4", "a, b"])
            writer.writerow(["https://example.com/2.mp4", "c"])

        with patch.object(importer, "verify_url", return_value=True):
            count, _ = importer.import_from_file(str(path))

        assert count == 2

    def test_oversized_file_is_rejected_without_reading(self, tmp_path):
        from batch_importer import BatchImporter

        queue = MagicMock()
        queue.MAX_QUEUE_SIZE = 1000
        importer = BatchImporter(queue, {})

        path = tmp_path / "huge.txt"
        path.write_text("x" * 1024, encoding="utf-8")
        # Simulate a very large file without allocating gigabytes
        with patch.object(Path, "stat") as stat_mock:
            stat_mock.return_value.st_size = 6 * 1024 * 1024
            with patch("builtins.open") as open_mock:
                count, truncated = importer.import_from_file(str(path))

        assert count == 0
        assert truncated is False
        open_mock.assert_not_called()

    def test_unsupported_extension_is_rejected(self, tmp_path):
        from batch_importer import BatchImporter

        queue = MagicMock()
        queue.MAX_QUEUE_SIZE = 1000
        importer = BatchImporter(queue, {})

        path = self._write(tmp_path, "links.md", "https://example.com/1.mp4\n")
        count, truncated = importer.import_from_file(str(path))

        assert count == 0
        assert truncated is False
        queue.add_item.assert_not_called()


# ---------------------------------------------------------------------------
# History manager: idempotent schema creation
# ---------------------------------------------------------------------------


class TestHistoryManagerIdempotency:
    def _isolated_manager(self, tmp_path, name: str):
        from history_manager import HistoryManager

        db_file = tmp_path / name
        HistoryManager._test_db_file = str(db_file)
        HistoryManager._db_initialized = False
        return HistoryManager, HistoryManager()

    def test_double_init_is_safe(self, tmp_path):
        HistoryManager, manager = self._isolated_manager(tmp_path, "history.db")
        try:
            HistoryManager.init_db()
            HistoryManager.init_db()  # must not raise "table already exists"
            HistoryManager.init_db()
            assert manager.get_history() == []
        finally:
            HistoryManager._db_initialized = False
            delattr(HistoryManager, "_test_db_file")

    def test_entries_round_trip(self, tmp_path):
        HistoryManager, manager = self._isolated_manager(tmp_path, "history2.db")
        try:
            manager.add_entry(
                {
                    "url": "https://example.com/x",
                    "title": "X",
                    "status": "Completed",
                    "filename": "x.mp4",
                    "filepath": "/tmp/x.mp4",
                    "file_size": 123,
                }
            )
            rows = manager.get_history(limit=10)
            assert len(rows) == 1
            assert rows[0]["url"] == "https://example.com/x"
        finally:
            HistoryManager._db_initialized = False
            delattr(HistoryManager, "_test_db_file")


# ---------------------------------------------------------------------------
# yt-dlp support detection: bounded cache
# ---------------------------------------------------------------------------


class TestYTDLPSupportCache:
    def test_cache_is_bounded(self):
        from downloader.engines.ytdlp import YTDLPWrapper

        original_cache = dict(YTDLPWrapper._SUPPORT_CACHE)
        try:
            YTDLPWrapper._SUPPORT_CACHE.clear()
            with patch("yt_dlp.extractor.gen_extractors", return_value=[]):
                for i in range(YTDLPWrapper._SUPPORT_CACHE_MAX + 50):
                    YTDLPWrapper.supports(f"https://example.com/{i}")
            assert len(YTDLPWrapper._SUPPORT_CACHE) <= YTDLPWrapper._SUPPORT_CACHE_MAX
        finally:
            YTDLPWrapper._SUPPORT_CACHE.clear()
            YTDLPWrapper._SUPPORT_CACHE.update(original_cache)

    def test_empty_url_is_unsupported(self):
        from downloader.engines.ytdlp import YTDLPWrapper

        assert YTDLPWrapper.supports("") is False


# ---------------------------------------------------------------------------
# Proxy validation
# ---------------------------------------------------------------------------


class TestProxyValidation:
    @pytest.mark.parametrize(
        "proxy",
        [
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "socks5://192.168.1.1:1080",
            "http://10.0.0.1:3128",
            "ftp://proxy.example.com:21",
            "http://user:pass@127.0.0.1:8080",
            "http://:8080",
            "http://proxy.example.com:99999",
        ],
    )
    def test_unsafe_or_invalid_proxies_are_rejected(self, proxy):
        from ui_utils import validate_proxy

        assert validate_proxy(proxy) is False

    @pytest.mark.parametrize(
        "proxy",
        [
            "",
            "http://8.8.8.8:8080",
            "socks5://user:pass@proxy.example.com:1080",
            "https://myproxy.com:3128",
        ],
    )
    def test_valid_proxies_accepted(self, proxy):
        from ui_utils import validate_proxy

        assert validate_proxy(proxy) is True

    def test_download_options_rejects_bad_proxy(self):
        options = DownloadOptions(url="https://example.com/v", proxy="ftp://x:1")
        with pytest.raises(ValueError):
            options.validate()

    def test_download_options_accepts_public_proxy(self):
        options = DownloadOptions(
            url="https://example.com/v", proxy="http://proxy.example.com:3128"
        )
        options.validate()  # must not raise


# ---------------------------------------------------------------------------
# Download options: time range semantics
# ---------------------------------------------------------------------------


class TestTimeRangeValidation:
    def test_open_ended_ranges_are_allowed(self):
        # start only / end only are both legitimate section downloads
        DownloadOptions(url="https://example.com/v", start_time="00:01:00").validate()
        DownloadOptions(url="https://example.com/v", end_time="00:02:00").validate()

    def test_inverted_range_is_rejected(self):
        options = DownloadOptions(
            url="https://example.com/v", start_time="00:02:00", end_time="00:01:00"
        )
        with pytest.raises(ValueError):
            options.validate()

    def test_negative_time_is_rejected(self):
        options = DownloadOptions(url="https://example.com/v", start_time="-5")
        with pytest.raises(ValueError):
            options.validate()


# ---------------------------------------------------------------------------
# Locale files: no missing keys, valid JSON
# ---------------------------------------------------------------------------


class TestLocales:
    def test_all_locales_are_valid_json_objects(self):
        root = Path(__file__).resolve().parents[1] / "locales"
        for locale_path in sorted(root.glob("*.json")):
            data = json.loads(locale_path.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"{locale_path.name} must be an object"

    def test_english_has_dashboard_refresh_key(self):
        root = Path(__file__).resolve().parents[1] / "locales"
        english = json.loads((root / "en.json").read_text(encoding="utf-8"))
        # Referenced by views/dashboard_view.py with a default; must exist so
        # translations are possible.
        assert "refresh_dashboard" in english

    def test_ui_hint_keys_exist(self):
        root = Path(__file__).resolve().parents[1] / "locales"
        english = json.loads((root / "en.json").read_text(encoding="utf-8"))
        for key in (
            "video_url_tooltip",
            "fetch_info_tooltip",
            "cookies_tooltip",
            "force_generic_tooltip",
        ):
            assert key in english


# ---------------------------------------------------------------------------
# Security: HTTP helpers always bound their wait time
# ---------------------------------------------------------------------------


class TestImportPathPolicy:
    """Import paths should allow user locations and deny system locations."""

    @pytest.mark.parametrize(
        "path",
        ["/etc/passwd", "/proc/self/environ", "/var/log/syslog", "/boot/grub"],
    )
    def test_system_paths_are_denied(self, path):
        from ui_utils import is_safe_path

        assert is_safe_path(path) is False

    def test_home_path_is_allowed(self):
        from ui_utils import is_safe_path

        assert is_safe_path(str(Path.home() / "Downloads" / "links.txt")) is True

    def test_temp_path_is_allowed(self, tmp_path):
        from ui_utils import is_safe_path

        # Users legitimately keep link lists outside their home directory.
        assert is_safe_path(str(tmp_path / "links.txt")) is True

    def test_empty_and_null_paths_are_denied(self):
        from ui_utils import is_safe_path

        assert is_safe_path("") is False
        assert is_safe_path("   ") is False
        assert is_safe_path("bad\x00name") is False

    def test_macos_symlinked_system_dirs_stay_denied(self, monkeypatch):
        """macOS reaches /etc, /var and /tmp through /private symlinks.

        Resolving the path alone turned ``/etc/passwd`` into
        ``/private/etc/passwd``, which matched no entry on the denylist, so the
        guard allowed reading system files on macOS only.  The macOS layout is
        simulated by rewriting ``realpath`` the way the OS does.
        """
        import posixpath

        from ui_utils import is_safe_path

        mapping = {
            "/etc": "/private/etc",
            "/var": "/private/var",
            "/tmp": "/private/tmp",
        }
        real_realpath = posixpath.realpath

        def mac_realpath(path, *args, **kwargs):
            text = str(path)
            if not text.startswith("/private"):
                for logical, physical in mapping.items():
                    if text == logical:
                        text = physical
                        break
                    if text.startswith(logical + "/"):
                        text = physical + text[len(logical) :]
                        break
            return real_realpath(text, *args, **kwargs)

        monkeypatch.setattr(posixpath, "realpath", mac_realpath)

        for denied in (
            "/etc/passwd",
            "/private/etc/passwd",
            "/var/log/syslog",
            "/private/var/log/syslog",
            "/private/var/db/anything.db",
        ):
            assert is_safe_path(denied) is False, denied

        # macOS keeps the per-user temporary directory under /private/var/folders
        # and users can legitimately import link lists from there.
        for allowed in (
            "/private/var/folders/ab/T/streamcatch/links.txt",
            "/var/folders/ab/T/streamcatch/links.txt",
            "/tmp/links.txt",
            "/private/tmp/links.txt",
            "/private/var/tmp/links.txt",
        ):
            assert is_safe_path(allowed) is True, allowed

    def test_symlink_out_of_a_temp_dir_is_denied(self, tmp_path):
        """A temp directory is not a loophole to reach a system file."""
        from ui_utils import is_safe_path

        link = tmp_path / "shortcut"
        try:
            link.symlink_to("/etc")
        except (
            OSError,
            NotImplementedError,
        ):  # pragma: no cover - Windows w/o privilege
            pytest.skip("symlinks are unavailable")

        assert is_safe_path(str(link / "passwd")) is False


class TestHttpTimeouts:
    def test_safe_request_applies_default_timeout(self):
        from ui_utils import DEFAULT_HTTP_TIMEOUT, safe_request_with_redirects

        fake_response = MagicMock()
        fake_response.is_redirect = False
        fake_response.is_permanent_redirect = False

        with (
            patch("ui_utils.validate_url", return_value=True),
            patch(
                "ui_utils.requests.request", return_value=fake_response
            ) as request_mock,
        ):
            safe_request_with_redirects("GET", "https://example.com/x")

        assert request_mock.call_args.kwargs["timeout"] == DEFAULT_HTTP_TIMEOUT

    def test_explicit_timeout_is_preserved(self):
        from ui_utils import safe_request_with_redirects

        fake_response = MagicMock()
        fake_response.is_redirect = False
        fake_response.is_permanent_redirect = False

        with (
            patch("ui_utils.validate_url", return_value=True),
            patch(
                "ui_utils.requests.request", return_value=fake_response
            ) as request_mock,
        ):
            safe_request_with_redirects("GET", "https://example.com/x", timeout=3)

        assert request_mock.call_args.kwargs["timeout"] == 3


# ---------------------------------------------------------------------------
# Downloading job: cancellation and error mapping
# ---------------------------------------------------------------------------


class TestDownloadJobStatusMapping:
    def test_cancelled_job_maps_to_cancelled_status(self, monkeypatch):
        import tasks

        qm = QueueManager()
        item = {"url": "https://example.com/v", "status": "Queued", "title": "v"}
        qm.add_item(item)

        recorded: list[tuple] = []

        def fake_update(item_id, status, updates=None):
            recorded.append((item_id, status, updates))

        monkeypatch.setattr(qm, "update_item_status", fake_update)
        monkeypatch.setattr(tasks.app_state.state, "queue_manager", qm)

        job = tasks.DownloadJob(item, page=None)
        job._handle_error(InterruptedError("Download Cancelled by user"))

        statuses = [entry[1] for entry in recorded]
        assert DownloadStatus.CANCELLED in statuses
        assert DownloadStatus.ERROR not in statuses

    def test_generic_error_maps_to_error_status(self, monkeypatch):
        import tasks

        qm = QueueManager()
        item = {"url": "https://example.com/v", "status": "Queued", "title": "v"}
        qm.add_item(item)

        recorded: list[tuple] = []
        monkeypatch.setattr(
            qm, "update_item_status", lambda *a, **k: recorded.append(a)
        )
        monkeypatch.setattr(tasks.app_state.state, "queue_manager", qm)

        job = tasks.DownloadJob(item, page=None)
        job._handle_error(RuntimeError("boom"))

        statuses = [entry[1] for entry in recorded]
        assert DownloadStatus.ERROR in statuses


# ---------------------------------------------------------------------------
# Scheduler helper
# ---------------------------------------------------------------------------


class TestSchedulerHelper:
    def test_none_returns_queued(self):
        from download_scheduler import DownloadScheduler

        status, when = DownloadScheduler.prepare_schedule(None)
        assert status == DownloadStatus.QUEUED
        assert when is None

    def test_past_time_rolls_to_next_day(self):
        from datetime import datetime, timedelta

        from download_scheduler import DownloadScheduler

        past = (datetime.now() - timedelta(minutes=5)).time()
        status, when = DownloadScheduler.prepare_schedule(past)
        assert status == DownloadStatus.SCHEDULED
        assert when is not None
        assert when > datetime.now()

    def test_invalid_type_raises(self):
        from download_scheduler import DownloadScheduler

        with pytest.raises(TypeError):
            DownloadScheduler.prepare_schedule("tomorrow")


# ---------------------------------------------------------------------------
# Rate limiter burst semantics
# ---------------------------------------------------------------------------


class TestRateLimiterBurst:
    def test_burst_then_throttle(self):
        from rate_limiter import RateLimiter

        limiter = RateLimiter(rate=1.0, capacity=3.0)
        assert [limiter.check() for _ in range(3)] == [True, True, True]
        assert limiter.check() is False

    def test_refill_over_time(self):
        from rate_limiter import RateLimiter

        limiter = RateLimiter(rate=50.0, capacity=1.0)
        assert limiter.check() is True
        assert limiter.check() is False
        time.sleep(0.05)
        assert limiter.check() is True


# ---------------------------------------------------------------------------
# Queue refresh: detached controls must never raise, and unchanged items must
# not push redundant update commands to the client
# ---------------------------------------------------------------------------


def _make_download_item(**overrides):
    item = {
        "id": "item-1",
        "url": "https://example.com/video.mp4",
        "status": "Downloading",
        "title": "Example video",
        "progress": 0.1,
        "speed": "1MB/s",
        "eta": "10s",
        "size": "10MB",
    }
    item.update(overrides)
    return item


def _make_item_control(item=None, page=None):
    from views.components.download_item import DownloadItemControl

    control = DownloadItemControl(
        item if item is not None else _make_download_item(),
        on_cancel=MagicMock(),
        on_retry=MagicMock(),
        on_remove=MagicMock(),
        on_play=MagicMock(),
        on_open_folder=MagicMock(),
    )
    control.page = page
    return control


class TestDownloadItemDetachedSafety:
    """The queue is repainted on a timer even when its view is not displayed."""

    def test_update_state_without_page_does_not_raise(self):
        control = _make_item_control(page=None)
        control.update = MagicMock()

        control.update_state(_make_download_item(status="Completed", progress=1.0))

        control.update.assert_not_called()
        assert control.status_text.value == LM.get("status_completed")
        assert control.progress_bar.value == 1.0

    def test_repeated_refresh_without_page_does_not_raise(self):
        control = _make_item_control(page=None)
        for _ in range(5):
            control.update_state(_make_download_item())
            control.update_progress()

    def test_safe_update_skips_when_unmounted_but_pushes_when_mounted(self):
        detached = _make_item_control(page=None)
        detached.update = MagicMock()
        detached._safe_update()
        detached.update.assert_not_called()

        page = MagicMock()
        mounted = _make_item_control(page=page)
        mounted._safe_update()
        page.update.assert_called_once_with(mounted)


class TestDownloadItemRepaintGating:
    """Only visible changes should cost a client update command."""

    def test_identical_state_is_not_repainted(self):
        control = _make_item_control(page=MagicMock())
        control.update = MagicMock()

        control.update_state(_make_download_item())

        control.update.assert_not_called()

    def test_progress_change_repaints_exactly_once(self):
        control = _make_item_control(page=MagicMock())
        control.update = MagicMock()

        control.update_state(_make_download_item(progress=0.42))

        control.update.assert_called_once()

    def test_speed_change_repaints(self):
        control = _make_item_control(page=MagicMock())
        control.update = MagicMock()

        control.update_state(_make_download_item(speed="2MB/s"))

        control.update.assert_called_once()

    def test_status_only_change_repaints_and_relabels(self):
        control = _make_item_control(page=MagicMock())
        control.update = MagicMock()

        control.update_state(_make_download_item(status="Error", error="boom"))

        control.update.assert_called_once()
        assert control.status_text.value == LM.get("status_error")

    def test_in_place_mutation_of_item_is_picked_up(self):
        item = _make_download_item()
        control = _make_item_control(item, page=MagicMock())
        control.update = MagicMock()

        item["progress"] = 0.5  # workers mutate the live queue item dict
        control.update_state(item)
        control.update.assert_called_once()
        # A second refresh with no further mutation is a no-op again.
        control.update.reset_mock()
        control.update_state(item)
        control.update.assert_not_called()


class TestQueueViewRefreshWithDetachedView:
    def _make_view(self, items, page):
        from queue_manager import QueueManager
        from views.queue_view import QueueView

        manager = QueueManager()
        for item in items:
            manager.add_item(dict(item))
        view = QueueView(
            manager,
            on_cancel=MagicMock(),
            on_remove=MagicMock(),
            on_reorder=MagicMock(),
            on_play=MagicMock(),
            on_open_folder=MagicMock(),
        )
        view.page = page
        return view, manager

    def test_rebuild_on_detached_view_renders_items(self):
        view, _ = self._make_view(
            [
                _make_download_item(id="a"),
                _make_download_item(id="b", status="Queued"),
            ],
            page=None,
        )

        view.rebuild()

        from views.components.download_item import DownloadItemControl

        rendered = [
            c for c in view.list_view.controls if isinstance(c, DownloadItemControl)
        ]
        assert [c.item["id"] for c in rendered] == ["a", "b"]

    def test_rebuild_skips_unchanged_items_and_updates_only_the_changed_one(self):
        view, manager = self._make_view(
            [
                _make_download_item(id="a"),
                _make_download_item(id="b", status="Queued", progress=0.0),
            ],
            page=MagicMock(),
        )
        view.rebuild()

        from views.components.download_item import DownloadItemControl

        controls = {
            c.item["id"]: c
            for c in view.list_view.controls
            if isinstance(c, DownloadItemControl)
        }
        assert set(controls) == {"a", "b"}
        for control in controls.values():
            # Flet attaches controls to the page when they are added to a
            # mounted hierarchy; the mocked view does not do that for us.
            control.page = MagicMock()
            control.update = MagicMock()

        view.rebuild()  # nothing changed
        assert controls["a"].update.call_count == 0
        assert controls["b"].update.call_count == 0

        manager.update_item_status("b", "Downloading", {"progress": 0.75})
        view.rebuild()

        assert controls["a"].update.call_count == 0
        assert controls["b"].update.call_count == 1

    def test_rebuild_after_view_is_detached_again_does_not_raise(self):
        view, _ = self._make_view([_make_download_item(id="a")], page=MagicMock())
        view.rebuild()

        view.page = None
        view.rebuild()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ---------------------------------------------------------------------------
# Shared detached-safe update helper (one canonical implementation)
# ---------------------------------------------------------------------------


class TestSafeUpdateHelper:
    def test_skips_unmounted_control(self):
        from ui_utils import safe_update

        control = ft.Container()
        control.update = MagicMock()

        assert safe_update(control) is False
        control.update.assert_not_called()

    def test_pushes_mounted_control(self):
        from ui_utils import safe_update

        control = ft.Container()
        page = MagicMock()
        control.page = page

        assert safe_update(control) is True
        page.update.assert_called_once_with(control)

    def test_swallows_failing_update(self):
        from ui_utils import safe_update

        control = ft.Container()
        control.page = MagicMock()
        control.update = MagicMock(side_effect=AssertionError("page went away"))

        assert safe_update(control) is False

    def test_preview_card_update_info_works_detached(self):
        from views.components.download_preview import DownloadPreviewCard

        card = DownloadPreviewCard()
        card.update_info({})  # hides the card; must not raise while detached
        assert card.visible is False

        card.update_info({"title": "Video", "filesize": 1024})
        assert card.visible is True
        assert card.title_text.value == "Video"


# ---------------------------------------------------------------------------
# History aggregates: total size used to be hard-coded to 0
# ---------------------------------------------------------------------------


class TestHistoryStats:
    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        from history_manager import HistoryManager

        monkeypatch.setattr(
            HistoryManager, "_test_db_file", tmp_path / "history.db", raising=False
        )
        return HistoryManager()

    @pytest.mark.parametrize(
        ("stored", "expected"),
        [
            (None, 0),
            (0, 0),
            (2048, 2048),
            ("2048", 2048),
            ("12.50 MB", int(12.5 * 1024**2)),
            ("1.00 GB", 1024**3),
            ("900 KiB", 900 * 1024),
            ("N/A", 0),
            ("", 0),
            ("not a size", 0),
        ],
    )
    def test_size_parsing(self, stored, expected):
        from history_manager import HistoryManager

        assert HistoryManager._parse_size_bytes(stored) == expected

    def _add(self, manager, size, url="https://example.com/a.mp4"):
        manager.add_entry(
            {
                "url": url,
                "title": "Video",
                "status": "Completed",
                "filename": "a.mp4",
                "filepath": "/tmp/a.mp4",
                "file_size": size,
            }
        )

    def test_stats_sum_mixed_storage_formats(self, manager):
        self._add(manager, "12.50 MB", "https://example.com/a.mp4")
        self._add(manager, 1048576, "https://example.com/b.mp4")  # 1 MB raw bytes
        self._add(manager, "N/A", "https://example.com/c.mp4")

        stats = manager.get_stats()

        assert stats["total_downloads"] == 3
        assert stats["total_size_mb"] == pytest.approx(13.5, abs=0.01)

    def test_stats_empty_history(self, manager):
        stats = manager.get_stats()

        assert stats == {"total_downloads": 0, "total_size_mb": 0}


class TestHistorySummaryLine:
    def _patch_manager(self, monkeypatch, stats):
        from app_state import state

        fake = MagicMock()
        fake.get_stats.return_value = stats
        monkeypatch.setattr(state, "history_manager", fake, raising=False)

    def test_summary_reports_totals(self, monkeypatch):
        from views.history_view import HistoryView

        self._patch_manager(monkeypatch, {"total_downloads": 3, "total_size_mb": 10.0})
        view = HistoryView()

        view._update_summary()

        assert "3" in view.summary_text.value
        assert "10.00 MB" in view.summary_text.value

    def test_summary_hidden_without_history(self, monkeypatch):
        from views.history_view import HistoryView

        self._patch_manager(monkeypatch, {"total_downloads": 0, "total_size_mb": 0})
        view = HistoryView()

        view._update_summary()

        assert view.summary_text.value == ""

    def test_summary_survives_broken_stats_source(self, monkeypatch):
        from views.history_view import HistoryView

        self._patch_manager(monkeypatch, None)
        view = HistoryView()

        view._update_summary()  # must not raise

        assert view.summary_text.value == ""


# ---------------------------------------------------------------------------
# Crash handler: secrets must not be written to the crash log
# ---------------------------------------------------------------------------


class TestCrashHandlerRedaction:
    def test_secret_locals_are_redacted_and_log_is_private(self, tmp_path, monkeypatch):
        import sys as _sys
        from pathlib import Path

        import main as main_module

        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        def trigger_failure():
            api_key = "top" + "-secret-value"  # value is not literal in the source
            password = "hunter2" + "!"
            raise ValueError("boom")

        with pytest.raises(SystemExit):
            try:
                trigger_failure()
            except ValueError:
                main_module.global_crash_handler(*_sys.exc_info())

        crash_log = tmp_path / ".streamcatch" / "crash.log"
        assert crash_log.exists()
        content = crash_log.read_text(encoding="utf-8")

        assert "top-secret-value" not in content
        assert "hunter2!" not in content
        assert "***REDACTED***" in content
        assert "ValueError" in content and "boom" in content

        # Crash logs can contain call arguments, so they must not be world-readable.
        mode = crash_log.stat().st_mode & 0o777
        assert mode & 0o077 == 0, f"crash log is too permissive: {oct(mode)}"


class TestQueueKeyboardSelectionSafety:
    """J/K/Delete shortcuts must be harmless while the queue is not displayed."""

    def _view_with_items(self, count=3):
        from queue_manager import QueueManager
        from views.queue_view import QueueView

        manager = QueueManager()
        for i in range(count):
            manager.add_item(
                _make_download_item(id=f"k{i}", title=f"item {i}", progress=0.0)
            )
        view = QueueView(
            manager,
            on_cancel=MagicMock(),
            on_remove=MagicMock(),
            on_reorder=MagicMock(),
            on_play=MagicMock(),
            on_open_folder=MagicMock(),
        )
        view.page = MagicMock()
        view.rebuild()
        return view

    def test_select_item_on_detached_view_does_not_raise(self):
        view = self._view_with_items()
        # Simulate the user navigating away: the view (and every control in it)
        # is no longer attached to the page.
        view.page = None
        for control in view.list_view.controls:
            control.page = None

        view.select_item(2)

        assert view.selected_index == 2
        selected = view.list_view.controls[2]
        assert selected.border is not None
        assert selected.shadow is not None

    def test_select_item_clamps_and_restores_previous_highlight(self):
        view = self._view_with_items()
        for control in view.list_view.controls:
            control.page = MagicMock()

        view.select_item(1)
        first = view.list_view.controls[0]
        assert first.border is None  # previous highlight cleared
        assert view.list_view.controls[1].border is not None

        view.select_item(0)
        assert view.list_view.controls[1].border is None
        assert view.list_view.controls[0].border is not None


# ---------------------------------------------------------------------------
# History export / import (backup and restore)
# ---------------------------------------------------------------------------


class TestHistoryImportExport:
    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        from history_manager import HistoryManager

        db = tmp_path / "history.db"
        monkeypatch.setattr(HistoryManager, "_test_db_file", db, raising=False)
        return HistoryManager()

    def _add(self, manager, url, size="1.00 MB"):
        manager.add_entry(
            {
                "url": url,
                "title": "Video",
                "status": "Completed",
                "filename": "v.mp4",
                "filepath": "/tmp/v.mp4",
                "file_size": size,
            }
        )

    def test_round_trip_into_a_fresh_database(self, manager, tmp_path):
        self._add(manager, "https://example.com/a.mp4", "12.50 MB")
        self._add(manager, "https://example.com/b.mp4", 1048576)
        backup = tmp_path / "backup.json"
        manager.export_to_json(str(backup))

        from history_manager import HistoryManager

        HistoryManager._test_db_file = tmp_path / "restored.db"
        restored = HistoryManager()

        assert restored.import_from_json_file(str(backup)) == (2, 0)
        assert restored.get_stats()["total_downloads"] == 2
        assert restored.get_stats()["total_size_mb"] == pytest.approx(13.5, abs=0.01)

    def test_import_is_idempotent(self, manager, tmp_path):
        self._add(manager, "https://example.com/a.mp4")
        backup = tmp_path / "backup.json"
        manager.export_to_json(str(backup))

        from history_manager import HistoryManager

        HistoryManager._test_db_file = tmp_path / "restored.db"
        restored = HistoryManager()
        assert restored.import_from_json_file(str(backup)) == (1, 0)
        assert restored.import_from_json_file(str(backup)) == (0, 1)
        assert restored.get_stats()["total_downloads"] == 1

    def test_original_timestamp_is_preserved(self, manager, tmp_path):
        backup = tmp_path / "old.json"
        backup.write_text(
            '[{"url": "https://old/1", "title": "Old", "status": "Completed",'
            ' "timestamp": "2019-03-04 05:06:07", "file_size": "3.00 MB"}]',
            encoding="utf-8",
        )

        assert manager.import_from_json_file(str(backup)) == (1, 0)
        assert str(manager.get_history()[0]["timestamp"]).startswith("2019-03-04")

    def test_import_accepts_a_wrapped_payload(self, manager, tmp_path):
        backup = tmp_path / "wrapped.json"
        backup.write_text(
            '{"history": [{"url": "https://x/1", "status": "Completed"}]}',
            encoding="utf-8",
        )

        assert manager.import_from_json_file(str(backup)) == (1, 0)

    def test_malformed_rows_are_skipped_without_aborting(self, manager):
        imported, skipped = manager.import_entries(
            [
                {"nope": 1},
                "not a dict",
                None,
                {"url": "https://ok/1", "status": "Completed"},
            ]
        )

        assert (imported, skipped) == (1, 3)
        assert manager.get_stats()["total_downloads"] == 1

    def test_non_list_payload_is_rejected(self, manager):
        assert manager.import_entries({"url": "https://x/1"}) == (0, 0)
        assert manager.import_entries("nope") == (0, 0)

    @pytest.mark.parametrize(
        ("content", "message"),
        [
            ("{not json", "not valid JSON"),
            ("[", "not valid JSON"),
        ],
    )
    def test_invalid_json_raises_a_clear_error(
        self, manager, tmp_path, content, message
    ):
        bad = tmp_path / "bad.json"
        bad.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match=message):
            manager.import_from_json_file(str(bad))

    def test_missing_file_raises_value_error(self, manager, tmp_path):
        with pytest.raises(ValueError):
            manager.import_from_json_file(str(tmp_path / "missing.json"))

    def test_oversized_file_is_rejected(self, manager, tmp_path):
        from history_manager import HistoryManager

        big = tmp_path / "big.json"
        big.write_text("[]", encoding="utf-8")
        with open(big, "a", encoding="utf-8") as handle:
            handle.write(" " * (HistoryManager.MAX_IMPORT_BYTES + 1))

        with pytest.raises(ValueError, match="larger than"):
            manager.import_from_json_file(str(big))

    def test_live_download_timestamp_is_left_to_the_database(self, manager):
        """Normal downloads must keep using the database default."""
        self._add(manager, "https://example.com/live.mp4")

        row = manager.get_history()[0]
        assert row["timestamp"]  # set by SQLite, not by the caller


class TestHistoryViewBackupButtons:
    def test_buttons_hidden_without_callbacks(self):
        from views.history_view import HistoryView

        view = HistoryView()

        assert view.export_btn.visible is False
        assert view.import_btn.visible is False

    def test_buttons_visible_and_dispatch_when_wired(self):
        from views.history_view import HistoryView

        on_export = MagicMock()
        on_import = MagicMock()
        view = HistoryView(on_export=on_export, on_import=on_import)

        assert view.export_btn.visible is True
        assert view.import_btn.visible is True

        view._on_export_click(None)
        view._on_import_click(None)

        on_export.assert_called_once()
        on_import.assert_called_once()

    def test_clicks_are_safe_without_callbacks(self):
        from views.history_view import HistoryView

        view = HistoryView()

        view._on_export_click(None)  # must not raise
        view._on_import_click(None)


class TestHistoryBackupControllerFlow:
    """The shared file picker must route results to the right flow."""

    def _controller(self):
        from unittest.mock import patch

        from app_controller import AppController

        page = MagicMock()
        page.overlay = []
        with patch("app_controller.AppController.start_background_loop"):
            controller = AppController(page, MagicMock())
        # The real picker is attached to the page overlay; the mock page does
        # not do that for us, and FilePicker.update() asserts on the page.
        controller.file_picker.page = MagicMock()
        return controller

    def test_export_writes_the_chosen_path(self, tmp_path, monkeypatch):
        from app_state import state

        controller = self._controller()
        manager = MagicMock()
        monkeypatch.setattr(state, "history_manager", manager)
        target = str(tmp_path / "backup.json")

        controller._finish_history_export(MagicMock(path=target))

        manager.export_to_json.assert_called_once_with(target)
        controller.page.open.assert_called()  # success snackbar

    def test_export_refuses_an_unsafe_destination(self, monkeypatch):
        from app_state import state

        controller = self._controller()
        manager = MagicMock()
        monkeypatch.setattr(state, "history_manager", manager)

        controller._finish_history_export(MagicMock(path="/etc/streamcatch.json"))

        manager.export_to_json.assert_not_called()
        controller.page.open.assert_called()  # failure snackbar

    def test_export_reports_failure_without_raising(self, tmp_path, monkeypatch):
        from app_state import state

        controller = self._controller()
        manager = MagicMock()
        manager.export_to_json.side_effect = OSError("disk full")
        monkeypatch.setattr(state, "history_manager", manager)

        controller._finish_history_export(MagicMock(path=str(tmp_path / "x.json")))

        controller.page.open.assert_called()

    def test_import_refreshes_the_history_view(self, tmp_path, monkeypatch):
        from app_state import state

        controller = self._controller()
        source = tmp_path / "backup.json"
        source.write_text("[]", encoding="utf-8")
        event = MagicMock()
        event.files = [MagicMock(path=str(source))]
        manager = MagicMock()
        manager.import_from_json_file.return_value = (2, 0)
        monkeypatch.setattr(state, "history_manager", manager)

        controller._finish_history_import(event)

        manager.import_from_json_file.assert_called_once_with(str(source))
        controller.ui.history_view.load.assert_called_once()

    def test_import_refuses_an_unsafe_source(self, monkeypatch):
        from app_state import state

        controller = self._controller()
        manager = MagicMock()
        monkeypatch.setattr(state, "history_manager", manager)
        event = MagicMock()
        event.files = [MagicMock(path="/etc/passwd")]

        controller._finish_history_import(event)

        manager.import_from_json_file.assert_not_called()

    def test_cancelled_dialogs_are_ignored(self, monkeypatch):
        from app_state import state

        controller = self._controller()
        manager = MagicMock()
        monkeypatch.setattr(state, "history_manager", manager)

        controller._finish_history_export(MagicMock(path=None))
        controller._finish_history_import(MagicMock(files=[]))

        manager.export_to_json.assert_not_called()
        manager.import_from_json_file.assert_not_called()

    def test_picker_action_routes_results(self):
        controller = self._controller()
        controller.file_picker.save_file = MagicMock()
        controller.file_picker.pick_files = MagicMock()

        controller.on_export_history()
        assert controller._picker_action == "history_export"
        controller.file_picker.save_file.assert_called_once()

        controller.on_import_history()
        assert controller._picker_action == "history_import"
        controller.file_picker.pick_files.assert_called_once()

        controller.on_batch_import()
        assert controller._picker_action == "batch_import"

    def test_picker_result_is_dispatched_by_action(self):
        controller = self._controller()
        controller.on_batch_file_result = MagicMock()
        controller._finish_history_export = MagicMock()
        controller._finish_history_import = MagicMock()

        controller._picker_action = "history_export"
        controller.on_file_picker_result(MagicMock())
        controller._finish_history_export.assert_called_once()

        controller._picker_action = "history_import"
        controller.on_file_picker_result(MagicMock())
        controller._finish_history_import.assert_called_once()

        controller._picker_action = "batch_import"
        controller.on_file_picker_result(MagicMock())
        controller.on_batch_file_result.assert_called_once()


# ---------------------------------------------------------------------------
# Application data directory: relocatable, and sandboxed during tests
# ---------------------------------------------------------------------------


class TestAppDataDirectory:
    def test_env_override_wins(self, monkeypatch, tmp_path):
        from app_paths import DATA_DIR_ENV, data_dir, data_file

        monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path / "data"))

        assert data_dir() == tmp_path / "data"
        assert data_file("history.db") == tmp_path / "data" / "history.db"

    def test_blank_override_falls_back_to_home(self, monkeypatch, tmp_path):
        from app_paths import DATA_DIR_ENV, data_dir

        monkeypatch.setenv(DATA_DIR_ENV, "   ")
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))

        assert data_dir() == tmp_path / ".streamcatch"

    def test_tilde_is_expanded(self, monkeypatch, tmp_path):
        from app_paths import DATA_DIR_ENV, data_dir

        # Tilde expansion consults $HOME (os.path.expanduser), not Path.home().
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv(DATA_DIR_ENV, "~/custom-streamcatch")

        assert data_dir() == tmp_path / "custom-streamcatch"

    def test_app_files_live_in_the_data_directory(self):
        """Config, history, and logs must follow the same overridable folder.

        The modules resolve their paths once, at import (application start), so
        the expectation is the directory that was active when they loaded —
        which for this session is the sandbox set by ``tests/conftest.py``.
        """
        from pathlib import Path

        import config_manager
        import history_manager
        import logger_config
        from app_paths import data_dir, data_file

        assert Path(config_manager.CONFIG_FILE).parent == data_dir()
        assert Path(history_manager.HistoryManager.DB_FILE).parent == data_dir()
        assert data_file("app.log").parent == data_dir()

        from app_paths import DEFAULT_DIR_NAME

        assert DEFAULT_DIR_NAME == ".streamcatch"
        assert logger_config is not None

    def test_test_session_never_touches_the_user_profile(self):
        """Guard: the suite must run against the sandboxed data directory.

        ``tests/conftest.py`` redirects ``STREAMCATCH_DATA_DIR`` before any
        application import; if that ever stops happening, a test run would
        append rows to the developer's real history database again.
        """
        import os
        import tempfile
        from pathlib import Path

        from app_paths import DATA_DIR_ENV, data_dir

        override = os.environ.get(DATA_DIR_ENV, "")
        assert override, f"{DATA_DIR_ENV} is not set for this test session"
        assert str(data_dir()).startswith(
            tempfile.gettempdir()
        ), f"tests are writing to {data_dir()}"
        assert data_dir() != Path.home() / ".streamcatch"
