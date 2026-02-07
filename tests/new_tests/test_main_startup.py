import pytest
from unittest.mock import MagicMock, patch
import sys
import logging

# Mock flet before importing main
with patch.dict(sys.modules, {"flet": MagicMock()}):
    import flet as ft
    import main


@pytest.fixture
def mock_dependencies():
    # Create mocks
    mock_lm = MagicMock()
    mock_state = MagicMock()
    mock_theme = MagicMock()
    mock_ui_cls = MagicMock()
    mock_controller_cls = MagicMock()

    # Setup behaviors
    mock_state.config = {"language": "en", "theme_mode": "dark"}
    mock_state.high_contrast = False
    mock_state.clipboard_monitor_active = False

    # Mock UI instance behavior
    mock_ui_instance = mock_ui_cls.return_value
    mock_ui_instance.initialize_views.return_value = MagicMock()

    return {
        "LM": mock_lm,
        "state": mock_state,
        "Theme": mock_theme,
        "UI_cls": mock_ui_cls,
        "Controller_cls": mock_controller_cls,
    }


def test_main_initialization_success(mock_dependencies):
    page = MagicMock()
    page.platform = "linux"

    # Directly patch the attributes in the main module object
    with (
        patch.object(main, "LM", mock_dependencies["LM"]),
        patch.object(main, "state", mock_dependencies["state"]),
        patch.object(main, "Theme", mock_dependencies["Theme"]),
        patch.object(main, "UIManager", mock_dependencies["UI_cls"]),
        patch.object(main, "AppController", mock_dependencies["Controller_cls"]),
    ):

        # Execute main
        main.main(page)

    # Verify
    mock_dependencies["LM"].load_language.assert_called_with("en")

    # Check if UI was instantiated
    mock_dependencies["UI_cls"].assert_called_with(page)
    # Check if initialize_views was called on the instance
    mock_dependencies["UI_cls"].return_value.initialize_views.assert_called()


def test_main_initialization_failure(mock_dependencies):
    page = MagicMock()

    mock_dependencies["LM"].load_language.side_effect = Exception("Config Error")

    with (
        patch.object(main, "LM", mock_dependencies["LM"]),
        patch.object(main, "state", mock_dependencies["state"]),
        patch.object(main, "Theme", mock_dependencies["Theme"]),
        patch.object(main, "UIManager", mock_dependencies["UI_cls"]),
        patch.object(main, "AppController", mock_dependencies["Controller_cls"]),
    ):

        with pytest.raises(Exception, match="Config Error"):
            main.main(page)

    page.clean.assert_called()
    page.add.assert_called()


def test_global_crash_handler_logging():
    with (
        patch.object(main.logger, "critical") as mock_critical,
        patch("builtins.open", new_callable=MagicMock) as mock_open,
        patch("os.name", "posix"),  # Force POSIX to avoid Windows MessageBox
    ):

        try:
            raise ValueError("Test Crash")
        except ValueError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            with patch("sys.exit"):
                main.global_crash_handler(exc_type, exc_value, exc_traceback)

        assert mock_critical.call_count >= 1
        mock_open.assert_called()
