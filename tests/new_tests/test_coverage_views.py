import unittest
from unittest.mock import MagicMock, patch


# Define MockControl first
class MockControl:
    def __init__(self, *args, **kwargs):
        self.visible = True
        self.value = ""
        self.controls = []
        self.disabled = False
        self.content = None
        self.padding = 0

        # Handle kwargs that match attributes
        for k, v in kwargs.items():
            setattr(self, k, v)


# Patch dependencies before importing views
with patch.dict(
    "sys.modules",
    {
        "flet": MagicMock(),
    },
):
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

    # Need to handle enum values
    ft.ScrollMode.AUTO = "auto"
    ft.MainAxisAlignment.SPACE_BETWEEN = "space_between"
    ft.MainAxisAlignment.START = "start"
    ft.MainAxisAlignment.END = "end"
    ft.MainAxisAlignment.CENTER = "center"
    ft.CrossAxisAlignment.START = "start"
    ft.CrossAxisAlignment.CENTER = "center"
    ft.NavigationRailLabelType.ALL = "all"
    ft.NavigationRailLabelType.NONE = "none"
    ft.FontWeight.BOLD = "bold"
    ft.TextOverflow.ELLIPSIS = "ellipsis"
    ft.ThemeMode.LIGHT = "light"
    ft.ThemeMode.DARK = "dark"
    ft.ThemeMode.SYSTEM = "system"
    ft.padding.symmetric = lambda horizontal, vertical: (horizontal, vertical)
    ft.border.all = lambda width, color: (width, color)
    ft.colors.with_opacity = lambda opacity, color: color

    from views.download_view import DownloadView
    from views.components.download_input_card import DownloadInputCard


class TestDownloadView(unittest.TestCase):
    def setUp(self):
        self.mock_fetch = MagicMock()
        self.mock_add = MagicMock()
        self.mock_paste = MagicMock()
        self.mock_batch = MagicMock()
        self.mock_schedule = MagicMock()
        self.mock_state = MagicMock()
        self.mock_state.config.get.return_value = "%(title)s.%(ext)s"

        # We need to mock BaseView init which calls super().__init__ and might use flet
        with (
            patch("views.base_view.BaseView.__init__"),
            patch("views.download_view.DownloadInputCard") as MockInputCard,
        ):

            # Setup Mock Input Card instance
            self.mock_input_card_instance = MockInputCard.return_value
            self.mock_input_card_instance.url_input = MagicMock()
            self.mock_input_card_instance.url_input.value = ""
            self.mock_input_card_instance.get_options.return_value = {}

            self.view = DownloadView(
                self.mock_fetch,
                self.mock_add,
                self.mock_paste,
                self.mock_batch,
                self.mock_schedule,
                self.mock_state,
            )

            # Replace the input_card attribute with our mock if it wasn't automatically
            self.view.input_card = self.mock_input_card_instance

        # Manually set attributes
        self.view.page = MagicMock()
        self.view.add_btn = MagicMock()
        self.view.preview_card = MagicMock()

    def test_initialization(self):
        # Verify components are created
        self.assertIsNotNone(self.view.input_card)
        self.assertIsNotNone(self.view.preview_card)

    def test_update_video_info_success(self):
        info = {
            "original_url": "https://youtube.com/watch?v=1",
            "title": "Vid",
            "thumbnail": "t",
            "duration": 100,
        }

        self.view.update_video_info(info)

        self.assertEqual(self.view.video_info, info)
        self.view.preview_card.update_info.assert_called_with(info)
        self.view.input_card.update_video_info.assert_called_with(info)
        self.assertFalse(self.view.add_btn.disabled)

    def test_update_video_info_none(self):
        self.view.update_video_info(None)
        self.assertIsNone(self.view.video_info)
        self.assertTrue(self.view.add_btn.disabled)
        self.view.input_card.update_video_info.assert_called_with(None)

    def test_on_add_click(self):
        # Setup InputCard options
        self.view.input_card.get_options.return_value = {
            "url": "http://test.com",
            "start_time": "00:00:10",
            "force_generic": True,
        }

        # Setup video info
        self.view.video_info = {"title": "Test Title"}

        self.view._on_add_click(None)

        self.mock_add.assert_called()
        args = self.mock_add.call_args[0][0]
        self.assertEqual(args["url"], "http://test.com")
        self.assertEqual(args["start_time"], "00:00:10")
        self.assertTrue(args["force_generic"])
        self.assertEqual(args["title"], "Test Title")

    def test_open_downloads_folder(self):
        with patch("views.download_view.open_folder") as mock_open:
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = MagicMock()
                self.view._open_downloads_folder()
                mock_open.assert_called()
