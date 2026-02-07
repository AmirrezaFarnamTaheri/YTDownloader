import pytest
from unittest.mock import MagicMock, patch
from views.settings_view import SettingsView
import flet as ft

class TestSettingsViewFull:
    @pytest.fixture
    def mock_config(self):
        return {
            "download_path": "/home/user/downloads",
            "proxy": "",
            "rate_limit": "",
            "output_template": "%(title)s.%(ext)s",
            "language": "en",
            "max_concurrent_downloads": 3,
            "theme_mode": "System",
            "high_contrast": False,
            "compact_mode": False,
            "use_aria2c": False,
            "gpu_accel": "None",
            "clipboard_monitor_enabled": False
        }

    @pytest.fixture
    def view(self, mock_config):
        return SettingsView(mock_config, lambda x: None, lambda x: None)

    def test_init_load(self, view):
        # Verify inputs populated
        assert view.download_path_input.value == "/home/user/downloads"
        assert view.max_concurrent_input.value == "3"
        assert view.theme_mode_dd.value == "System"

    def test_save_valid_inputs(self, view):
        view.page = MagicMock()
        view.download_path_input.value = "/tmp/downloads"
        view.max_concurrent_input.value = "5"

        with patch("views.settings_view.ConfigManager.save_config") as mock_save:
             with patch("tasks.configure_concurrency") as mock_cc:
                  # Mock validation functions
                  with patch("views.settings_view.validate_download_path", return_value=True):
                      with patch("views.settings_view.validate_proxy", return_value=True):
                          with patch("views.settings_view.validate_rate_limit", return_value=True):
                              with patch("views.settings_view.validate_output_template", return_value=True):
                                  view.save_settings(None)

                                  mock_save.assert_called()
                                  assert view.config["max_concurrent_downloads"] == 5
                                  assert view.config["download_path"] == "/tmp/downloads"

    def test_save_invalid_download_path(self, view):
        view.page = MagicMock()
        view.download_path_input.value = "/invalid/path"

        with patch("views.settings_view.validate_download_path", return_value=False):
             view.save_settings(None)

             # SnackBar shown
             view.page.open.assert_called()
             args, _ = view.page.open.call_args
             snack = args[0]
             assert isinstance(snack, ft.SnackBar)
             assert snack.bgcolor == "#EF4444" # Theme.Status.ERROR

    def test_save_invalid_max_concurrent(self, view):
        view.page = MagicMock()
        view.max_concurrent_input.value = "invalid"

        with patch("views.settings_view.validate_download_path", return_value=True):
            # Other validations pass
             with patch("views.settings_view.validate_proxy", return_value=True):
                 with patch("views.settings_view.validate_rate_limit", return_value=True):
                      with patch("views.settings_view.validate_output_template", return_value=True):
                          view.save_settings(None)
                          view.page.open.assert_called()

    def test_toggle_high_contrast(self, view):
        view.page = MagicMock()
        e = MagicMock()
        e.control.value = True

        with patch("views.settings_view.ConfigManager.save_config") as mock_save:
            view._on_high_contrast_change(e)

            assert view.config["high_contrast"] is True
            mock_save.assert_called()
            # Theme updated
            assert view.page.theme is not None # Should be high contrast theme mock

    def test_toggle_compact_mode(self, view):
        view.page = MagicMock()
        e = MagicMock()
        e.control.value = True

        mock_cb = MagicMock()
        view.on_compact_mode_change = mock_cb

        with patch("views.settings_view.ConfigManager.save_config") as mock_save:
            view._on_compact_mode_change(e)

            assert view.config["compact_mode"] is True
            mock_save.assert_called()
            mock_cb.assert_called_with(True)

    def test_theme_change(self, view):
        view.page = MagicMock()
        view.theme_mode_dd.value = "Dark"

        with patch("views.settings_view.ConfigManager.save_config") as mock_save:
            view._on_theme_change(None)

            assert view.page.theme_mode == ft.ThemeMode.DARK
            assert view.config["theme_mode"] == "Dark"
            mock_save.assert_called()
# Patch sys.modules to mock tasks for configure_concurrency
import sys
if "tasks" not in sys.modules:
    sys.modules["tasks"] = MagicMock()
