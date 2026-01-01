
import unittest
from unittest.mock import MagicMock, patch

# Mock controls must be defined before imports that use them
class MockControl:
    def __init__(self, *args, **kwargs):
        self.visible = True
        self.value = ""
        self.controls = []
        self.disabled = False
        self.content = None
        self.url_input = None
        self.fetch_btn = None

        # Helper to mimic Flet control properties
        for k, v in kwargs.items():
            setattr(self, k, v)

    def update(self): pass

with patch.dict("sys.modules", {
    "flet": MagicMock(),
}):
    import flet as ft

    # Configure flet mocks
    ft.UserControl = MagicMock
    ft.Container = MockControl
    ft.Column = MockControl
    ft.Row = MockControl
    ft.ListView = MockControl
    ft.Text = MockControl
    ft.Icon = MockControl
    ft.TextField = MockControl
    ft.ElevatedButton = MockControl
    ft.IconButton = MockControl
    ft.FloatingActionButton = MockControl
    ft.NavigationRail = MockControl
    ft.NavigationRailDestination = MockControl
    ft.NavigationBar = MockControl
    ft.ResponsiveRow = MockControl
    ft.Chip = MockControl
    ft.ExpansionTile = MockControl
    ft.Dropdown = MockControl
    ft.Checkbox = MockControl
    ft.ProgressBar = MockControl
    ft.Divider = MockControl
    ft.PieChart = MockControl
    ft.BarChart = MockControl

    # Enums
    ft.TextThemeStyle.HEADLINE_MEDIUM = "headline_medium"
    ft.TextThemeStyle.BODY_MEDIUM = "body_medium"
    ft.FontWeight.BOLD = "bold"
    ft.MainAxisAlignment.SPACE_BETWEEN = "space_between"
    ft.MainAxisAlignment.START = "start"
    ft.MainAxisAlignment.END = "end"
    ft.CrossAxisAlignment.START = "start"
    ft.ScrollMode.AUTO = "auto"
    ft.icons.DOWNLOAD = "download"
    ft.colors.with_opacity = lambda o, c: c

    from views.download_view import DownloadView
    from views.components.download_input_card import DownloadInputCard

class TestViewInteractions(unittest.TestCase):
    def setUp(self):
        self.mock_page = MagicMock()
        self.mock_fetch = MagicMock()
        self.mock_add = MagicMock()
        self.mock_paste = MagicMock()
        self.mock_import = MagicMock()
        self.mock_schedule = MagicMock()
        self.mock_state = MagicMock()
        self.mock_state.config.get.return_value = "en"

        # Patch BaseView init to avoid super() issues if complex
        with patch("views.base_view.BaseView.__init__"):
            self.view = DownloadView(
                self.mock_fetch,
                self.mock_add,
                self.mock_paste,
                self.mock_import,
                self.mock_schedule,
                self.mock_state
            )
            # Manually inject controls created in __init__ because we patched it out?
            # Actually, if we patch BaseView.__init__, DownloadView.__init__ runs but skips super().
            # DownloadView.__init__ creates controls.
            # However, since we are mocking flet classes with MockControl, they should instantiate fine.
            # But we need to ensure super().__init__ (which sets self.app_title etc) doesn't break things if skipped.
            # DownloadView doesn't rely heavily on BaseView init for these tests.
            pass

        # Re-run _build_ui or ensure controls exist
        # If we patched BaseView.__init__, DownloadView.__init__ logic *after* super() call runs.
        # So self.input_card etc should exist.

    def test_fetch_button_click(self):
        # We need to find the input card in the view's controls
        # or use the direct reference if we rely on DownloadView structure
        input_card = self.view.input_card
        self.assertIsNotNone(input_card)

        # Simulate input
        input_card.url_input = MockControl()
        input_card.url_input.value = "https://youtube.com/watch?v=123"
        input_card.fetch_btn = MockControl()

        # Call the handler on InputCard directly
        # The View passes `self.on_fetch_info` to InputCard.
        # InputCard calls `self.on_fetch(url)`.

        # We can test that InputCard's fetch logic works
        input_card._on_fetch_click(None)

        self.mock_fetch.assert_called_with("https://youtube.com/watch?v=123")

    def test_fetch_empty_url(self):
        input_card = self.view.input_card
        input_card.url_input = MockControl()
        input_card.url_input.value = ""

        input_card._on_fetch_click(None)

        self.mock_fetch.assert_not_called()
        # Check error text logic if implemented in MockControl
        # self.assertIsNotNone(input_card.url_input.error_text)

    def test_add_to_queue_click(self):
        # Mock input card data
        self.view.input_card.get_options = MagicMock(return_value={
            "url": "http://vid",
            "video_format": "best"
        })

        # Simulate video info presence
        self.view.video_info = {"title": "Test Video"}

        # Call handler
        self.view._on_add_click(None)

        self.mock_add.assert_called()
        args = self.mock_add.call_args[0][0]
        self.assertEqual(args["url"], "http://vid")
        self.assertEqual(args["title"], "Test Video")

if __name__ == '__main__':
    unittest.main()
