"""
Additional coverage for modules that previously had thin test coverage.

Focuses on pure logic: RSS parsing, Telegram extraction, preview card
formatting, responsive layout decisions, and clipboard polling.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# RSS manager
# ---------------------------------------------------------------------------


RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>My Channel</title>
    <item>
      <title>Episode 1</title>
      <link>https://example.com/ep1</link>
      <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Bad entry</title>
      <link>not-a-url</link>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <title>Video Feed</title>
  <entry>
    <title>Video One</title>
    <link href="https://example.com/watch?v=1"/>
    <published>2024-01-01T10:00:00+00:00</published>
    <yt:videoId>abc123</yt:videoId>
  </entry>
</feed>
"""


class TestRSSManagerParsing:
    def _response(self, text: str, status: int = 200):
        response = MagicMock()
        response.status_code = status
        response.headers = {"Content-Length": str(len(text.encode()))}
        response.encoding = "utf-8"
        response.apparent_encoding = "utf-8"
        response.text = text
        response.raise_for_status = MagicMock()
        return response

    def test_parse_rss_items(self):
        from rss_manager import RSSManager

        # Only the feed URL is trusted here; item links still go through the
        # real validator, which must drop the malformed "not-a-url" entry.
        with (
            patch(
                "rss_manager.safe_request_with_redirects",
                return_value=self._response(RSS_SAMPLE),
            ),
            patch(
                "rss_manager.validate_url",
                side_effect=lambda url, **kw: url.startswith("https://"),
            ),
        ):
            items = RSSManager.parse_feed("https://example.com/feed.xml")

        assert len(items) == 1
        assert items[0]["title"] == "Episode 1"
        assert items[0]["is_video"] is False

    def test_parse_atom_items(self):
        from rss_manager import RSSManager

        with (
            patch(
                "rss_manager.safe_request_with_redirects",
                return_value=self._response(ATOM_SAMPLE),
            ),
            patch("rss_manager.validate_url", return_value=True),
        ):
            items = RSSManager.parse_feed("https://example.com/atom.xml")

        assert len(items) == 1
        assert items[0]["video_id"] == "abc123"
        assert items[0]["is_video"] is True

    def test_invalid_url_returns_empty(self):
        from rss_manager import RSSManager

        with patch("rss_manager.validate_url", return_value=False):
            assert RSSManager.parse_feed("file:///etc/passwd") == []

    def test_oversized_content_length_is_rejected(self):
        from rss_manager import RSSManager

        response = self._response(RSS_SAMPLE)
        response.headers = {"Content-Length": str(50 * 1024 * 1024)}
        with (
            patch("rss_manager.safe_request_with_redirects", return_value=response),
            patch("rss_manager.validate_url", return_value=True),
        ):
            assert RSSManager.parse_feed("https://example.com/feed.xml") == []

    def test_malformed_xml_fails_closed(self):
        from rss_manager import RSSManager

        with (
            patch(
                "rss_manager.safe_request_with_redirects",
                return_value=self._response("<rss><channel><title>x</title>"),
            ),
            patch("rss_manager.validate_url", return_value=True),
        ):
            assert RSSManager.parse_feed("https://example.com/feed.xml") == []

    def test_network_error_returns_empty(self):
        import requests

        from rss_manager import RSSManager

        with (
            patch(
                "rss_manager.safe_request_with_redirects",
                side_effect=requests.RequestException("boom"),
            ),
            patch("rss_manager.validate_url", return_value=True),
        ):
            assert RSSManager.parse_feed("https://example.com/feed.xml") == []


class TestRSSManagerFeedBookkeeping:
    def _manager(self, feeds=None):
        from rss_manager import RSSManager

        config = {"rss_feeds": feeds or []}
        return RSSManager(config), config

    def test_add_feed_normalizes_and_deduplicates(self):
        manager, config = self._manager(["https://a.com/feed"])
        with (
            patch("rss_manager.validate_url", return_value=True),
            patch.object(manager, "_save_feeds"),
        ):
            manager.add_feed("https://b.com/feed")
            manager.add_feed("https://b.com/feed")  # duplicate

        assert len(manager.get_feeds()) == 2

    def test_add_feed_rejects_invalid_url(self):
        manager, _ = self._manager()
        with (
            patch("rss_manager.validate_url", return_value=False),
            patch.object(manager, "_save_feeds") as save_mock,
        ):
            manager.add_feed("ftp://nope")

        assert manager.get_feeds() == []
        save_mock.assert_not_called()

    def test_remove_feed(self):
        manager, _ = self._manager(["https://a.com/feed", "https://b.com/feed"])
        with patch.object(manager, "_save_feeds"):
            manager.remove_feed("https://a.com/feed")

        urls = [feed["url"] for feed in manager.get_feeds()]
        assert urls == ["https://b.com/feed"]

    def test_normalizes_legacy_string_feeds(self):
        manager, _ = self._manager(["https://a.com/feed"])
        assert manager.get_feeds()[0]["name"] == "https://a.com/feed"

    def test_normalizes_dict_feeds_and_drops_broken_entries(self):
        manager, _ = self._manager(
            [
                {"url": "https://a.com/feed", "name": "A"},
                {"name": "missing-url"},
                "  ",
            ]
        )
        feeds = manager.get_feeds()
        assert len(feeds) == 1
        assert feeds[0]["name"] == "A"


# ---------------------------------------------------------------------------
# Telegram extractor
# ---------------------------------------------------------------------------


class TestTelegramExtractor:
    def test_is_telegram_url_matches_only_telegram_hosts(self):
        from downloader.extractors.telegram import TelegramExtractor

        assert TelegramExtractor.is_telegram_url("https://t.me/channel/1") is True
        assert TelegramExtractor.is_telegram_url("https://telegram.me/x") is True
        assert TelegramExtractor.is_telegram_url("https://example.com/t.me/1") is False
        assert TelegramExtractor.is_telegram_url("not a url") is False

    def _page(self, html: str):
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.iter_content = lambda chunk_size=8192: iter([html.encode()])
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=response)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    def test_metadata_extracts_video_and_title(self):
        from downloader.extractors.telegram import TelegramExtractor

        html = """
        <html><head>
          <meta property="og:description" content="Cool Clip"/>
          <meta property="og:image" content="https://cdn.example.com/thumb.jpg"/>
        </head><body>
          <video src="https://cdn.example.com/video.mp4"></video>
        </body></html>
        """
        with (
            patch(
                "downloader.extractors.telegram.safe_request_with_redirects",
                return_value=self._page(html),
            ),
            patch("downloader.extractors.telegram.validate_url", return_value=True),
        ):
            meta = TelegramExtractor.get_metadata("https://t.me/channel/1")

        assert meta is not None
        assert meta["url"] == "https://cdn.example.com/video.mp4"
        assert meta["title"] == "Cool Clip"
        assert meta["thumbnail"] == "https://cdn.example.com/thumb.jpg"

    def test_metadata_uses_og_video_when_no_video_tag(self):
        from downloader.extractors.telegram import TelegramExtractor

        html = """
        <html><head>
          <meta property="og:description" content="Clip"/>
          <meta property="og:video" content="https://cdn.example.com/v.mp4"/>
        </head><body></body></html>
        """
        with (
            patch(
                "downloader.extractors.telegram.safe_request_with_redirects",
                return_value=self._page(html),
            ),
            patch("downloader.extractors.telegram.validate_url", return_value=True),
        ):
            meta = TelegramExtractor.get_metadata("https://t.me/channel/1")

        assert meta["url"] == "https://cdn.example.com/v.mp4"

    def test_metadata_returns_none_without_media(self):
        from downloader.extractors.telegram import TelegramExtractor

        with (
            patch(
                "downloader.extractors.telegram.safe_request_with_redirects",
                return_value=self._page("<html><body>nothing</body></html>"),
            ),
            patch("downloader.extractors.telegram.validate_url", return_value=True),
        ):
            assert TelegramExtractor.get_metadata("https://t.me/channel/1") is None

    def test_metadata_rejects_unsafe_extracted_url(self):
        from downloader.extractors.telegram import TelegramExtractor

        html = '<html><body><video src="http://127.0.0.1/secret"></video></body></html>'
        with (
            patch(
                "downloader.extractors.telegram.safe_request_with_redirects",
                return_value=self._page(html),
            ),
            patch("downloader.extractors.telegram.validate_url", return_value=False),
        ):
            assert TelegramExtractor.get_metadata("https://t.me/channel/1") is None

    def test_oversized_response_is_aborted(self):
        from downloader.extractors.telegram import TelegramExtractor

        chunk = b"x" * (1024 * 1024)
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.iter_content = lambda chunk_size=8192: iter([chunk, chunk, chunk])
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=response)
        ctx.__exit__ = MagicMock(return_value=False)

        with (
            patch(
                "downloader.extractors.telegram.safe_request_with_redirects",
                return_value=ctx,
            ),
            patch("downloader.extractors.telegram.validate_url", return_value=True),
        ):
            assert TelegramExtractor.get_metadata("https://t.me/channel/1") is None

    def test_extract_propagates_download_result(self):
        from downloader.extractors.telegram import TelegramExtractor

        meta = {"url": "https://cdn.example.com/v.mp4", "title": "My Video!"}
        with (
            patch.object(TelegramExtractor, "get_metadata", return_value=meta),
            patch(
                "downloader.engines.generic.GenericDownloader.download",
                return_value={
                    "filename": "MyVideo.mp4",
                    "filepath": "/tmp/MyVideo.mp4",
                },
            ) as download_mock,
        ):
            result = TelegramExtractor.extract("https://t.me/c/1", "/tmp")

        assert result["filename"] == "MyVideo.mp4"
        # Title is sanitized to a filesystem-safe name
        assert download_mock.call_args.kwargs["filename"] == "MyVideo.mp4"

    def test_extract_raises_when_no_media(self):
        from downloader.extractors.telegram import TelegramExtractor

        with patch.object(TelegramExtractor, "get_metadata", return_value=None):
            with pytest.raises(ValueError):
                TelegramExtractor.extract("https://t.me/c/1", "/tmp")


# ---------------------------------------------------------------------------
# Download preview card
# ---------------------------------------------------------------------------


class TestDownloadPreviewCard:
    def test_update_info_populates_fields(self):
        from views.components.download_preview import DownloadPreviewCard

        card = DownloadPreviewCard()
        card.update = MagicMock()
        card.update_info(
            {
                "title": "My Video",
                "thumbnail": "https://img.example.com/t.jpg",
                "duration_string": "1:23",
                "uploader": "Creator",
                "resolution": "1080p",
                "filesize": 1048576,
                "extractor_key": "Youtube",
            }
        )

        assert card.visible is True
        assert card.title_text.value == "My Video"
        assert card.thumbnail.src == "https://img.example.com/t.jpg"
        assert card.duration_text.value == "1:23"
        assert card.author_text.value == "Creator"
        assert card.format_text.value == "1080p"
        assert card.size_text.value == "1.00 MB"
        assert card.source_text.value == "Youtube"

    def test_update_info_falls_back_to_defaults(self):
        from views.components.download_preview import DownloadPreviewCard

        card = DownloadPreviewCard()
        card.update = MagicMock()
        card.update_info({"title": "Only Title"})

        assert card.duration_text.value  # localized N/A
        assert card.size_text.value == "N/A"
        assert card.format_text.value  # localized unknown

    def test_update_info_with_empty_dict_hides_card(self):
        from views.components.download_preview import DownloadPreviewCard

        card = DownloadPreviewCard()
        card.update = MagicMock()
        card.visible = True
        card.update_info({})

        assert card.visible is False

    def test_accepts_alternative_size_keys(self):
        from views.components.download_preview import DownloadPreviewCard

        card = DownloadPreviewCard()
        card.update = MagicMock()
        card.update_info({"title": "T", "filesize_approx": 2048})
        assert card.size_text.value == "2.00 KB"


# ---------------------------------------------------------------------------
# Responsive layout
# ---------------------------------------------------------------------------


class TestAppLayoutResponsiveness:
    def _layout(self, compact=False):
        from app_layout import AppLayout

        page = MagicMock()
        page.overlay = []
        page.navigation_bar = None
        page.update = MagicMock()
        return AppLayout(page, lambda e: None, compact_mode=compact), page

    def test_mobile_breakpoint_uses_bottom_navigation(self):
        layout, page = self._layout()
        layout.handle_resize(500, 900)

        assert layout.sidebar_container.visible is False
        assert page.navigation_bar is layout.bottom_nav

    def test_tablet_breakpoint_uses_compact_rail(self):
        layout, _ = self._layout()
        layout.handle_resize(900, 900)

        assert layout.sidebar_container.visible is True
        assert layout.rail.extended is False
        assert layout.sidebar_container.width == 72

    def test_desktop_breakpoint_uses_extended_rail(self):
        layout, _ = self._layout()
        layout.handle_resize(1600, 900)

        assert layout.rail.extended is True
        assert layout.sidebar_container.width == 200

    def test_forced_compact_mode_overrides_wide_window(self):
        layout, _ = self._layout(compact=True)
        layout.handle_resize(1600, 900)

        assert layout.rail.extended is False
        assert layout.sidebar_container.width == 72

    def test_returning_from_mobile_restores_sidebar(self):
        layout, page = self._layout()
        layout.handle_resize(500, 900)
        assert page.navigation_bar is not None

        layout.handle_resize(1600, 900)
        assert page.navigation_bar is None
        assert layout.sidebar_container.visible is True

    def test_set_navigation_index_updates_both_navigators(self):
        layout, _ = self._layout()
        layout.toggle_mobile_mode(True)

        layout.set_navigation_index(3)

        assert layout.rail.selected_index == 3
        assert layout.bottom_nav.selected_index == 3

    def test_toggle_compact_mode_changes_padding(self):
        layout, _ = self._layout()
        layout.toggle_compact_mode(True)
        assert layout.content_area.padding == 10
        layout.toggle_compact_mode(False)
        assert layout.content_area.padding == 20


# ---------------------------------------------------------------------------
# Clipboard monitor
# ---------------------------------------------------------------------------


class TestClipboardMonitor:
    def setup_method(self):
        # The monitor keeps module-level thread state between tests
        import clipboard_monitor

        clipboard_monitor._monitor_thread = None

    def test_start_returns_false_when_clipboard_unavailable(self):
        import pyperclip

        from clipboard_monitor import start_clipboard_monitor

        with patch.object(
            pyperclip, "paste", side_effect=pyperclip.PyperclipException("no clipboard")
        ):
            assert start_clipboard_monitor(MagicMock(), MagicMock()) is False

    def test_start_spawns_single_thread(self):
        from clipboard_monitor import start_clipboard_monitor

        page = MagicMock()
        view = MagicMock()
        with (
            patch("clipboard_monitor.pyperclip.paste", return_value="x"),
            patch("clipboard_monitor.threading.Thread") as thread_cls,
        ):
            thread_cls.return_value.is_alive.return_value = True
            assert start_clipboard_monitor(page, view) is True
            assert start_clipboard_monitor(page, view) is True  # already running
            assert thread_cls.call_count == 1

    def test_loop_detects_url_and_schedules_ui_update(self):
        import clipboard_monitor
        from app_state import state
        from clipboard_monitor import _clipboard_loop

        page = MagicMock()
        view = MagicMock()
        view.url_input = MagicMock()
        view.url_input.value = ""

        original_active = state.clipboard_monitor_active
        original_content = state.last_clipboard_content
        state.clipboard_monitor_active = True
        state.shutdown_flag.clear()
        state.last_clipboard_content = ""

        scheduled: list = []

        def fake_run_on_ui_thread(_page, callback, *args, **kwargs):
            scheduled.append(callback)
            # Execute immediately, as the real UI thread eventually would.
            callback(*args, **kwargs)

        call_count = {"n": 0}

        def fake_sleep(_seconds):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                state.shutdown_flag.set()

        try:
            with (
                patch(
                    "clipboard_monitor.pyperclip.paste",
                    return_value="https://example.com/video",
                ),
                patch("clipboard_monitor.validate_url", return_value=True),
                patch(
                    "clipboard_monitor.run_on_ui_thread",
                    side_effect=fake_run_on_ui_thread,
                ),
                patch("time.sleep", side_effect=fake_sleep),
            ):
                _clipboard_loop(page, view)

            assert scheduled, "clipboard URL should trigger a UI update"
            assert view.url_input.value == "https://example.com/video"
        finally:
            # Never leak global shutdown state into other tests
            state.shutdown_flag.clear()
            state.clipboard_monitor_active = original_active
            state.last_clipboard_content = original_content


# ---------------------------------------------------------------------------
# Config manager round-trips
# ---------------------------------------------------------------------------


class TestConfigManagerRoundTrip:
    def test_save_then_load_preserves_values(self, tmp_path, monkeypatch):
        from config_manager import ConfigManager

        config_file = tmp_path / "config.json"
        monkeypatch.setattr(
            ConfigManager, "_resolve_config_file", staticmethod(lambda: config_file)
        )

        payload = ConfigManager.DEFAULTS.copy()
        payload["theme_mode"] = "Light"
        payload["max_concurrent_downloads"] = 7
        ConfigManager.save_config(payload)

        reloaded = ConfigManager.load_config()
        assert reloaded["theme_mode"] == "Light"
        assert reloaded["max_concurrent_downloads"] == 7

    def test_corrupt_config_is_backed_up_and_defaults_restored(
        self, tmp_path, monkeypatch
    ):
        from config_manager import ConfigManager

        config_file = tmp_path / "config.json"
        config_file.write_text("{ this is not json", encoding="utf-8")
        monkeypatch.setattr(
            ConfigManager, "_resolve_config_file", staticmethod(lambda: config_file)
        )

        loaded = ConfigManager.load_config()

        assert loaded["theme_mode"] == ConfigManager.DEFAULTS["theme_mode"]
        assert (tmp_path / "config.json.bak").exists()

    def test_cookies_are_never_written_to_disk(self, tmp_path, monkeypatch):
        from config_manager import ConfigManager

        config_file = tmp_path / "config.json"
        monkeypatch.setattr(
            ConfigManager, "_resolve_config_file", staticmethod(lambda: config_file)
        )

        payload = ConfigManager.DEFAULTS.copy()
        payload["cookies"] = "SESSION=super-secret"
        ConfigManager.save_config(payload)

        raw = config_file.read_text(encoding="utf-8")
        assert "super-secret" not in raw
        assert "cookies" not in json.loads(raw)

    def test_invalid_theme_mode_is_rejected(self):
        from config_manager import ConfigManager

        payload = ConfigManager.DEFAULTS.copy()
        payload["theme_mode"] = "neon-disco"
        with pytest.raises(ValueError):
            ConfigManager._validate_schema(payload)

    def test_output_template_traversal_is_rejected(self):
        from config_manager import ConfigManager

        payload = ConfigManager.DEFAULTS.copy()
        payload["output_template"] = "../escape/%(title)s.%(ext)s"
        with pytest.raises(ValueError):
            ConfigManager._validate_schema(payload)


# ---------------------------------------------------------------------------
# Sync: never destroy local history with an unvalidated payload
# ---------------------------------------------------------------------------


class TestSyncHistoryValidation:
    """Regression: sync-down used to overwrite history.db with any payload.

    A corrupt, truncated, or unrelated file from the cloud (or from an import
    archive) would silently replace the user's history database, after which
    every history query failed with "file is not a database".
    """

    def _manager(self, tmp_path):
        from sync_manager import SyncManager

        config = MagicMock()
        config.load_config.return_value = {}
        cloud = MagicMock()
        history = MagicMock()
        history._resolve_db_file.return_value = str(tmp_path / "live_history.db")
        return SyncManager(cloud, config, history_manager=history)

    def test_json_payload_is_rejected(self, tmp_path):
        manager = self._manager(tmp_path)
        target = tmp_path / "live_history.db"
        target.write_bytes(b"SQLite format 3\x00" + b"\x00" * 32)

        bogus = tmp_path / "downloaded.db"
        bogus.write_text(json.dumps({"remote": "config"}), encoding="utf-8")

        assert manager._replace_history_db(str(bogus)) is False
        # The live database must be untouched
        assert target.read_bytes().startswith(b"SQLite format 3\x00")

    def test_truncated_sqlite_payload_is_rejected(self, tmp_path):
        manager = self._manager(tmp_path)
        target = tmp_path / "live_history.db"
        target.write_bytes(b"SQLite format 3\x00" + b"\x00" * 32)

        bogus = tmp_path / "truncated.db"
        # Valid magic header, garbage body -> integrity check must fail
        bogus.write_bytes(b"SQLite format 3\x00" + b"not a real db" * 4)

        assert manager._replace_history_db(str(bogus)) is False
        assert target.read_bytes().startswith(b"SQLite format 3\x00")

    def test_valid_sqlite_payload_is_accepted_and_backed_up(self, tmp_path):
        import sqlite3

        incoming = tmp_path / "incoming.db"
        with sqlite3.connect(incoming) as conn:
            conn.execute(
                "CREATE TABLE history (id INTEGER PRIMARY KEY, url TEXT, title TEXT,"
                " status TEXT, timestamp DATETIME, filename TEXT, filepath TEXT,"
                " file_size TEXT)"
            )
            conn.execute(
                "INSERT INTO history (url, title, status) VALUES (?, ?, ?)",
                ("https://example.com/x", "X", "Completed"),
            )

        target = tmp_path / "live_history.db"
        with sqlite3.connect(target) as conn:
            conn.execute(
                "CREATE TABLE history (id INTEGER PRIMARY KEY, url TEXT, title TEXT,"
                " status TEXT, timestamp DATETIME, filename TEXT, filepath TEXT,"
                " file_size TEXT)"
            )

        manager = self._manager(tmp_path)
        manager.history._resolve_db_file.return_value = str(target)

        assert manager._replace_history_db(str(incoming)) is True
        assert (tmp_path / "live_history.db.bak").exists()
        assert manager._is_valid_history_db(str(target)) is True

    def test_sync_down_keeps_local_db_when_remote_is_invalid(
        self, tmp_path, monkeypatch
    ):
        import sqlite3

        target = tmp_path / "live_history.db"
        with sqlite3.connect(target) as conn:
            conn.execute("CREATE TABLE history (id INTEGER PRIMARY KEY, url TEXT)")

        manager = self._manager(tmp_path)
        manager.history._resolve_db_file.return_value = str(target)

        def fake_download(filename, local_path):
            # 'history.db' comes back as unrelated JSON (corrupt/foreign payload)
            with open(local_path, "w", encoding="utf-8") as handle:
                handle.write('{"remote": "config"}')
            return True

        manager.cloud.download_file.side_effect = fake_download
        monkeypatch.setattr(manager, "_apply_config_snapshot", lambda _cfg: None)

        manager.sync_down()

        # Local history survives
        assert manager._is_valid_history_db(str(target)) is True
        with sqlite3.connect(target) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        assert ("history",) in tables
