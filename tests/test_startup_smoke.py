"""
End-to-end startup smoke test.

Every other UI test either mocks Flet or builds controls in isolation. This one
drives ``main.main(page)`` against a *real* ``flet.Page`` with a stubbed
transport, which is the only way to catch mistakes that only appear when the
whole tree is mounted (bad control kwargs, page-level API misuse, background
service wiring, cleanup ordering).

Skipped automatically when Flet is unavailable and the suite falls back to the
conftest mock.
"""

import asyncio
from unittest.mock import MagicMock

import flet as ft
import pytest


def _real_flet_available() -> bool:
    """True when a genuine Flet implementation is importable."""
    return (
        not isinstance(ft.Page, MagicMock) and getattr(ft, "__file__", None) is not None
    )


pytestmark = pytest.mark.skipif(
    not _real_flet_available(),
    reason="real flet runtime not available (conftest mock in use)",
)


class _FakePubSubHub:
    def subscribe(self, *args, **kwargs):
        return 0

    def unsubscribe(self, *args, **kwargs):
        return 0

    def unsubscribe_all(self, *args, **kwargs):
        pass


class _Result:
    def __init__(self, results=None):
        self.results = results or []


class _FakeConn:
    """Minimal stand-in for flet's websocket connection."""

    def __init__(self):
        self.commands = []
        self.pubsubhub = _FakePubSubHub()

    def send_commands(self, session_id, commands):
        self.commands.extend(commands)
        # Flet parses each result string for control ids.
        return _Result([""] * len(commands))

    def send_message(self, message):
        self.commands.append(message)

    def dispose(self):
        pass


@pytest.fixture
def clean_main_globals():
    """Reset module-level singletons around the smoke test."""
    import main as app_main
    from app_state import state

    saved = (app_main.PAGE, app_main.UI, app_main.CONTROLLER)
    try:
        yield app_main, state
    finally:
        try:
            if app_main.CONTROLLER is not None:
                app_main.CONTROLLER.cleanup()
        except Exception:  # pragma: no cover - cleanup is best effort
            pass
        app_main.PAGE, app_main.UI, app_main.CONTROLLER = saved
        state.shutdown_flag.set()


def test_main_builds_and_mounts_the_full_ui(clean_main_globals):
    app_main, state = clean_main_globals
    state.shutdown_flag.clear()

    loop = asyncio.new_event_loop()
    conn = _FakeConn()
    page = ft.Page(conn=conn, session_id="smoke", loop=loop)

    try:
        app_main.main(page)
    finally:
        state.shutdown_flag.set()
        loop.close()

    # The layout must be mounted on the page
    assert len(page.controls) == 1
    root = page.controls[0]
    assert isinstance(root, ft.Row)  # AppLayout extends Row
    assert len(root.controls) == 3  # sidebar, divider, content

    # Commands were actually sent to the client (i.e. the UI rendered)
    assert conn.commands, "no UI commands were sent to the client"


def test_main_registers_every_navigation_destination(clean_main_globals):
    app_main, state = clean_main_globals
    state.shutdown_flag.clear()

    loop = asyncio.new_event_loop()
    page = ft.Page(conn=_FakeConn(), session_id="smoke-nav", loop=loop)

    try:
        app_main.main(page)
        ui = app_main.UI
        assert ui is not None
        assert [type(view).__name__ for view in ui.views_list] == [
            "DashboardView",
            "DownloadView",
            "QueueView",
            "HistoryView",
            "RSSView",
            "SettingsView",
        ]
        # Every view must be reachable through the navigation rail
        assert len(ui.app_layout.rail.destinations) == len(ui.views_list)
    finally:
        state.shutdown_flag.set()
        loop.close()


def test_theme_refresh_survives_a_real_page(clean_main_globals):
    """refresh_theme() must not raise once the tree is mounted on a real page."""
    app_main, state = clean_main_globals
    state.shutdown_flag.clear()

    loop = asyncio.new_event_loop()
    page = ft.Page(conn=_FakeConn(), session_id="smoke-theme", loop=loop)

    try:
        app_main.main(page)
        ui = app_main.UI
        assert ui is not None

        from theme import Theme

        Theme.apply_theme_mode("light")
        try:
            ui.refresh_theme()
        finally:
            Theme.apply_theme_mode("dark")

        assert len(page.controls) == 1
        assert page.controls[0] is ui.app_layout
    finally:
        state.shutdown_flag.set()
        loop.close()
