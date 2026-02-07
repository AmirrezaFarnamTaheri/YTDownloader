from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from views.components.download_input_card import DownloadInputCard
from views.settings_view import SettingsView


class TestSettingsFeatures:

    @pytest.fixture
    def mock_config(self):
        return {"theme_mode": "System", "high_contrast": False, "compact_mode": False}

    @pytest.fixture
    def settings_view(self, mock_config):
        return SettingsView(mock_config, lambda x: None, lambda x: None)

    def test_theme_switch_high_contrast(self, settings_view):
        settings_view.page = MagicMock()
        e = MagicMock()
        settings_view.theme_mode_dd.value = "High Contrast"

        with patch("views.settings_view.ConfigManager.save_config") as mock_save:
            settings_view._on_theme_change(e)

            # Verify high contrast theme applied
            assert settings_view.page.theme is not None
            # We can't easily check if it is "High Contrast" object without implementation details,
            # but we can check calls.
            # Assuming Theme.get_high_contrast_theme() was called.
            # We can check config update
            assert settings_view.config["theme_mode"] == "High Contrast"
            mock_save.assert_called()

    def test_compact_mode_persistence(self, settings_view):
        settings_view.page = MagicMock()
        e = MagicMock()
        e.control.value = True

        mock_cb = MagicMock()
        settings_view.on_compact_mode_change = mock_cb

        with patch("views.settings_view.ConfigManager.save_config") as mock_save:
            settings_view._on_compact_mode_change(e)

            assert settings_view.config["compact_mode"] is True
            mock_save.assert_called()
            mock_cb.assert_called_with(True)


class TestDownloadInputCardFeatures:

    def test_search_query_transformation(self):
        mock_fetch = MagicMock()
        card = DownloadInputCard(mock_fetch, lambda x: None, MagicMock())
        card.page = MagicMock()  # For update()

        # input: "funny cat videos" (no url)
        card.url_input.value = "funny cat videos"

        card._on_fetch_click(None)

        # Verify fetch called with prefix
        mock_fetch.assert_called_with("ytsearch1:funny cat videos")

    def test_url_no_transformation(self):
        mock_fetch = MagicMock()
        card = DownloadInputCard(mock_fetch, lambda x: None, MagicMock())
        card.page = MagicMock()

        # input: "http://youtube.com/v"
        card.url_input.value = "http://youtube.com/v"

        card._on_fetch_click(None)

        # Verify fetch called as is
        mock_fetch.assert_called_with("http://youtube.com/v")

    def test_tooltips_presence(self):
        card = DownloadInputCard(lambda x: None, lambda x: None, MagicMock())

        assert card.url_input.tooltip is not None
        assert card.fetch_btn.tooltip is not None
        assert card.time_start.tooltip is not None
        assert card.time_end.tooltip is not None
        assert card.cookies_dd.tooltip is not None
        assert card.force_generic_cb.tooltip is not None
