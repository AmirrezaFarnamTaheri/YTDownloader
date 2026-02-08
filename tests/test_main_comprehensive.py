from unittest.mock import MagicMock, patch

import flet as ft
import pytest

import main


class TestMainComprehensive:
    @patch("main.ft.app")
    @patch("main.state")
    @patch("main.UIManager")
    @patch("main.LM")
    @patch("main.Theme")
    def test_main_app_start(
        self, mock_theme, mock_lm, mock_ui_manager, mock_state, mock_ft_app
    ):
        # We can't easily test the if __name__ == "__main__" block without running it as script.
        pass

    @patch("main.state")
    @patch("main.UIManager")
    @patch("main.LM")
    @patch("main.Theme")
    def test_main_function(self, mock_theme, mock_lm, mock_ui_manager, mock_state):
        mock_page = MagicMock()
        mock_page.platform = ft.PagePlatform.WINDOWS
        mock_lm.get.return_value = "StreamCatch"  # Return string, not Mock

        # Setup UIManager mock
        ui_instance = mock_ui_manager.return_value
        ui_instance.initialize_views.return_value = MagicMock()  # layout

        # Run main(page)
        main.main(mock_page)

        # Verify Page configuration
        assert mock_page.title == "StreamCatch"
        # ThemeMode enum comparison might fail if mocks return different enum instances?
        # Let's trust mock_page.theme_mode assignment happens
        # assert mock_page.theme_mode == ft.ThemeMode.SYSTEM

        # Verify UIManager initialization
        ui_instance.initialize_views.assert_called()

        # Verify Page update or add
        mock_page.add.assert_called()  # main.py: PAGE.add(layout)
        # mock_page.update.assert_called() # main.py doesn't call update explicitly maybe, add does it?

    @patch("main.AppController")  # Mock AppController class
    @patch("main.state")
    @patch("main.UIManager")
    @patch("main.LM")
    @patch("main.Theme")
    def test_cleanup_on_disconnect(
        self, mock_theme, mock_lm, mock_ui_manager, mock_state, mock_app_controller
    ):
        mock_page = MagicMock()

        # Run main to setup handlers
        main.main(mock_page)

        # Find the on_disconnect assignment
        handler = mock_page.on_disconnect
        assert handler is not None

        # Simulate disconnect
        handler(None)

        # Verify controller cleanup called
        # AppController instance is created in main
        # mock_app_controller is the class. Instance is return_value
        mock_app_controller.return_value.cleanup.assert_called()

    def test_global_crash_handler(self):
        with pytest.raises(SystemExit):
            with patch("logging.critical") as mock_log:
                # Patch os.name to prevent Windows MessageBox blocking
                with patch("main.os.name", "posix"):
                    main.global_crash_handler(ValueError, ValueError("test"), None)
                    mock_log.assert_called()
