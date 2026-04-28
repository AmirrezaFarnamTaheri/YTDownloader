from unittest.mock import MagicMock, patch

from localization_manager import LocalizationManager as LM
from views.dashboard_view import DashboardView


def _chip_value(chip):
    return chip.content.controls[2].value


def test_dashboard_sync_health_shows_running_when_worker_alive():
    LM.load_language("en")
    view = DashboardView(
        on_navigate=MagicMock(),
        on_paste_url=MagicMock(),
        on_batch_import=MagicMock(),
        queue_manager=MagicMock(),
    )

    fake_state = MagicMock()
    fake_state.config.get.side_effect = lambda key, default=None: {
        "auto_sync_enabled": True,
        "max_concurrent_downloads": 4,
        "metadata_cache_size": 20,
    }.get(key, default)
    fake_state.ffmpeg_available = True
    fake_state.sync_manager.is_auto_sync_running.return_value = True

    with patch("app_state.state", fake_state), patch(
        "views.dashboard_view.shutil.disk_usage",
        return_value=(100, 70, 30),
    ):
        view._refresh_health()

    assert _chip_value(view.health_chips_row.controls[1]) == "Running"


def test_dashboard_sync_health_distinguishes_enabled_from_running():
    LM.load_language("en")
    view = DashboardView(
        on_navigate=MagicMock(),
        on_paste_url=MagicMock(),
        on_batch_import=MagicMock(),
        queue_manager=MagicMock(),
    )

    fake_state = MagicMock()
    fake_state.config.get.side_effect = lambda key, default=None: {
        "auto_sync_enabled": True,
        "max_concurrent_downloads": 2,
        "metadata_cache_size": 50,
    }.get(key, default)
    fake_state.ffmpeg_available = False
    fake_state.sync_manager.is_auto_sync_running.return_value = False

    with patch("app_state.state", fake_state), patch(
        "views.dashboard_view.shutil.disk_usage",
        return_value=(100, 90, 10),
    ):
        view._refresh_health()

    assert _chip_value(view.health_chips_row.controls[1]) == "Enabled"
