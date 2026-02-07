import logging
import sys
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

# Configure logging to capture import errors
logger = logging.getLogger(__name__)


def pytest_configure(config):
    """
    Pytest hook to configure the environment before tests run.
    We attempt to import flet. If it fails (common in CI/headless without shared libs),
    we mock it so that tests can be collected and run (where possible).
    """
    try:
        import flet as ft

        # Try to access a property to ensure it's fully loaded
        _ = ft.PagePlatform.ANDROID
    except (ImportError, OSError, AttributeError) as e:
        logger.warning(
            f"Flet import failed: {e}. Mocking flet and dependencies for tests."
        )
        mock_dependencies()


def mock_dependencies():
    """Mocks flet and other runtime dependencies in sys.modules."""
    flet_mock = MagicMock()

    # Define base classes for inheritance
    class MockControl:
        def __init__(self, *args, **kwargs):
            self.content = kwargs.get("content")
            self.controls = kwargs.get("controls", [])
            self.value = kwargs.get("value")
            self.page = None
            self.overlay = []
            self.visible = kwargs.get("visible", True)
            self.padding = kwargs.get("padding", 0)
            self.disabled = kwargs.get("disabled", False)

            # Handle positional args for controls list (common in Row, Column, ListView)
            if not self.controls and args and isinstance(args[0], list):
                self.controls = args[0]

            # Allow any other attribute to be set
            for k, v in kwargs.items():
                if k not in [
                    "visible",
                    "padding",
                    "disabled",
                    "content",
                    "controls",
                    "value",
                ]:
                    setattr(self, k, v)

        def update(self):
            pass

        def run_task(self, func, *args, **kwargs):
            # Mock behavior for page.run_task
            pass

    class MockContainer(MockControl):
        pass

    class MockUserControl(MockControl):
        pass

    class MockView(MockControl):
        pass

    class MockSnackBar(MockControl):
        def __init__(self, content=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.content = content

    class MockText(MockControl):
        def __init__(self, value=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if value is not None:
                self.value = value

    class MockTextField(MockControl):
        pass

    class MockCheckbox(MockControl):
        pass

    class MockDropdown(MockControl):
        class Option:
            def __init__(self, key, text=None):
                self.key = key
                self.text = text

        pass

    class MockListView(MockControl):
        pass

    class MockTabs(MockControl):
        def __init__(self, tabs=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.tabs = tabs if tabs else []

    class MockNavigationRail(MockControl):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.destinations = kwargs.get("destinations", [])
            self.selected_index = kwargs.get("selected_index", 0)
            self.extended = kwargs.get("extended", False)

    class MockNavigationRailDestination(MockControl):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.icon = kwargs.get("icon")
            self.selected_icon = kwargs.get("selected_icon")
            self.label = kwargs.get("label")

    class MockPage(MockControl):
        platform = "linux"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.overlay = []

        def launch_url(self, url):
            pass

        def update(self):
            pass

        def open(self, control):
            pass

        def close(self, control):
            pass

        def set_clipboard(self, data):
            pass

    class MockRow(MockControl):
        pass

    class MockColumn(MockControl):
        pass

    class MockIcon(MockControl):
        def __init__(self, name=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.name = name

    class MockTextButton(MockControl):
        pass

    class MockIconButton(MockControl):
        pass

    class MockOutlinedButton(MockControl):
        pass

    class MockAlertDialog(MockControl):
        pass

    class MockExpansionTile(MockControl):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.title = kwargs.get("title")
            self.subtitle = kwargs.get("subtitle")
            self.controls = kwargs.get("controls", [])

    class MockFilePicker(MockControl):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.on_result = kwargs.get("on_result")

        def pick_files(self, *args, **kwargs):
            pass

    class MockFilePickerResultEvent:
        def __init__(self, files=None, path=None):
            self.files = files
            self.path = path

    class MockProgressBar(MockControl):
        pass

    class MockProgressRing(MockControl):
        pass

    class MockSwitch(MockControl):
        pass

    class MockRadio(MockControl):
        pass

    class MockRadioGroup(MockControl):
        pass

    class MockSlider(MockControl):
        pass

    class MockImage(MockControl):
        pass

    class MockDivider(MockControl):
        pass

    class MockTab(MockControl):
        pass

    class MockElevatedButton(MockControl):
        pass

    class MockPopupMenuItem(MockControl):
        pass

    class MockPopupMenuButton(MockControl):
        pass

    class MockTimePicker(MockControl):
        pass

    class MockDatePicker(MockControl):
        pass

    class MockPieChart(MockControl):
        pass

    class MockBarChart(MockControl):
        pass

    class MockResponsiveRow(MockControl):
        pass

    class MockChip(MockControl):
        pass

    class MockFloatingActionButton(MockControl):
        pass

    class MockNavigationBar(MockControl):
        pass

    # Assign classes to the mock
    flet_mock.Container = MockContainer
    flet_mock.UserControl = MockUserControl
    flet_mock.View = MockView
    flet_mock.Page = MockPage
    flet_mock.Control = MockControl
    flet_mock.SnackBar = MockSnackBar
    flet_mock.Text = MockText
    flet_mock.TextField = MockTextField
    flet_mock.Checkbox = MockCheckbox
    flet_mock.Dropdown = MockDropdown
    flet_mock.dropdown = MagicMock()
    flet_mock.dropdown.Option = MockDropdown.Option

    flet_mock.ListView = MockListView
    flet_mock.Tabs = MockTabs
    flet_mock.NavigationRail = MockNavigationRail
    flet_mock.NavigationRailDestination = MockNavigationRailDestination
    flet_mock.Row = MockRow
    flet_mock.Column = MockColumn
    flet_mock.Icon = MockIcon
    flet_mock.TextButton = MockTextButton
    flet_mock.IconButton = MockIconButton
    flet_mock.OutlinedButton = MockOutlinedButton
    flet_mock.AlertDialog = MockAlertDialog
    flet_mock.ExpansionTile = MockExpansionTile
    flet_mock.FilePicker = MockFilePicker
    flet_mock.FilePickerResultEvent = MockFilePickerResultEvent
    flet_mock.ProgressBar = MockProgressBar
    flet_mock.ProgressRing = MockProgressRing
    flet_mock.Switch = MockSwitch
    flet_mock.Radio = MockRadio
    flet_mock.RadioGroup = MockRadioGroup
    flet_mock.Slider = MockSlider
    flet_mock.Image = MockImage
    flet_mock.Divider = MockDivider
    flet_mock.Tab = MockTab
    flet_mock.ElevatedButton = MockElevatedButton
    flet_mock.PopupMenuItem = MockPopupMenuItem
    flet_mock.PopupMenuButton = MockPopupMenuButton
    flet_mock.TimePicker = MockTimePicker
    flet_mock.DatePicker = MockDatePicker
    flet_mock.PieChart = MockPieChart
    flet_mock.BarChart = MockBarChart
    flet_mock.ResponsiveRow = MockResponsiveRow
    flet_mock.Chip = MockChip
    flet_mock.FloatingActionButton = MockFloatingActionButton
    flet_mock.NavigationBar = MockNavigationBar

    # Explicitly map inputs to MockControl to ensure they maintain state (value)
    flet_mock.TextField = MockControl
    flet_mock.Dropdown = MockControl
    flet_mock.Checkbox = MockControl

    # Mock Enums
    flet_mock.PagePlatform = MagicMock()
    flet_mock.PagePlatform.ANDROID = "android"
    flet_mock.PagePlatform.IOS = "ios"
    flet_mock.PagePlatform.MACOS = "macos"
    flet_mock.PagePlatform.WINDOWS = "windows"
    flet_mock.PagePlatform.LINUX = "linux"
    flet_mock.PagePlatform.WEB = "web"

    flet_mock.MainAxisAlignment = MagicMock()
    flet_mock.CrossAxisAlignment = MagicMock()
    flet_mock.TextOverflow = MagicMock()
    flet_mock.FontWeight = MagicMock()
    flet_mock.TextAlign = MagicMock()

    flet_mock.NavigationRailLabelType = MagicMock()
    flet_mock.NavigationRailLabelType.ALL = "all"

    flet_mock.VisualDensity = MagicMock()
    flet_mock.VisualDensity.COMFORTABLE = "comfortable"

    flet_mock.ScrollMode = MagicMock()
    flet_mock.ScrollMode.AUTO = "auto"
    flet_mock.ScrollMode.ALWAYS = "always"
    flet_mock.ScrollMode.HIDDEN = "hidden"

    flet_mock.ThemeMode = MagicMock()
    flet_mock.ThemeMode.DARK = "dark"
    flet_mock.ThemeMode.LIGHT = "light"
    flet_mock.ThemeMode.SYSTEM = "system"

    flet_mock.ClipBehavior = MagicMock()
    flet_mock.ClipBehavior.HARD_EDGE = "hard_edge"

    flet_mock.ImageFit = MagicMock()
    flet_mock.ImageFit.COVER = "cover"
    flet_mock.ImageFit.CONTAIN = "contain"

    flet_mock.TextThemeStyle = MagicMock()
    flet_mock.TextThemeStyle.HEADLINE_MEDIUM = "headline_medium"
    flet_mock.TextThemeStyle.BODY_MEDIUM = "body_medium"

    flet_mock.KeyboardType = MagicMock()
    flet_mock.KeyboardType.NUMBER = "number"

    flet_mock.InputFilter = MagicMock()
    flet_mock.RoundedRectangleBorder = MagicMock()
    flet_mock.ButtonStyle = MagicMock()
    flet_mock.BoxShadow = MagicMock()
    flet_mock.BorderSide = MagicMock()
    flet_mock.border = MagicMock()
    flet_mock.border.all = MagicMock(return_value=MagicMock())
    flet_mock.border_radius = MagicMock()
    flet_mock.border_radius.only = MagicMock(return_value=MagicMock())
    flet_mock.padding = MagicMock()
    flet_mock.padding.symmetric = MagicMock(return_value=MagicMock())
    flet_mock.padding.only = MagicMock(return_value=MagicMock())
    flet_mock.alignment = MagicMock()

    flet_mock.PieChartSection = MagicMock()
    flet_mock.BarChartGroup = MagicMock()
    flet_mock.BarChartRod = MagicMock()
    flet_mock.ChartAxis = MagicMock()
    flet_mock.ChartAxisLabel = MagicMock()
    flet_mock.ChartGridLines = MagicMock()

    # Mock colors and icons - need to return string values for icon access
    class IconsMock:
        """Mock that returns the attribute name as the value for any icon access."""

        def __getattr__(self, name):
            return name  # Return the icon name as a string

    class ColorsMock:
        """Mock that returns the attribute name for any color access."""

        def __getattr__(self, name):
            return f"#{name}"

        @staticmethod
        def with_opacity(opacity, color):
            return f"{color}_{opacity}"

    flet_mock.colors = ColorsMock()
    flet_mock.icons = IconsMock()

    # Replace in sys.modules
    sys.modules["flet"] = flet_mock
    # Also ensure flet.auth and other submodules don't crash if imported
    sys.modules["flet.auth"] = MagicMock()
    sys.modules["flet.security"] = MagicMock()
    # Mock flet.controls.material.icons for any code that imports it directly
    sys.modules["flet.controls"] = MagicMock()
    sys.modules["flet.controls.material"] = MagicMock()
    sys.modules["flet.controls.material.icons"] = IconsMock()

    # Mock other runtime dependencies that might be missing in minimal CI envs
    # This ensures tests can be collected even if dependencies are missing.

    # pypresence
    if "pypresence" not in sys.modules:
        sys.modules["pypresence"] = MagicMock()

    # yt_dlp
    if "yt_dlp" not in sys.modules:
        yt_dlp_mock = MagicMock()

        class MockDownloadError(Exception):
            pass

        yt_dlp_mock.utils.DownloadError = MockDownloadError
        sys.modules["yt_dlp"] = yt_dlp_mock
        # Ensure submodules are also mocked if imported directly
        sys.modules["yt_dlp.utils"] = MagicMock()
        sys.modules["yt_dlp.utils"].DownloadError = MockDownloadError

    # PyDrive2
    if "pydrive2" not in sys.modules:
        sys.modules["pydrive2"] = MagicMock()
        sys.modules["pydrive2.auth"] = MagicMock()
        sys.modules["pydrive2.drive"] = MagicMock()

    # pyperclip
    if "pyperclip" not in sys.modules:
        sys.modules["pyperclip"] = MagicMock()

    # PIL
    if "PIL" not in sys.modules:
        sys.modules["PIL"] = MagicMock()
        sys.modules["PIL.Image"] = MagicMock()

    # requests
    if "requests" not in sys.modules:
        requests_mock = MagicMock()

        class MockRequestException(Exception):
            pass

        class MockConnectionError(MockRequestException):
            pass

        class MockHTTPError(MockRequestException):
            pass

        class MockTimeout(MockRequestException):
            pass

        class MockTooManyRedirects(MockRequestException):
            pass

        requests_mock.RequestException = MockRequestException
        requests_mock.ConnectionError = MockConnectionError
        requests_mock.HTTPError = MockHTTPError
        requests_mock.Timeout = MockTimeout
        requests_mock.TooManyRedirects = MockTooManyRedirects

        # Also patch exceptions submodule if accessed
        requests_mock.exceptions.RequestException = MockRequestException
        requests_mock.exceptions.ConnectionError = MockConnectionError
        requests_mock.exceptions.HTTPError = MockHTTPError
        requests_mock.exceptions.Timeout = MockTimeout
        requests_mock.exceptions.TooManyRedirects = MockTooManyRedirects

        sys.modules["requests"] = requests_mock

    # defusedxml - use real ElementTree for parsing in tests
    if "defusedxml" not in sys.modules:
        dxml = MagicMock()
        dxml_et = MagicMock()
        # Delegate parsing to real ET
        dxml_et.fromstring = ET.fromstring
        dxml.ElementTree = dxml_et
        sys.modules["defusedxml"] = dxml
        sys.modules["defusedxml.ElementTree"] = dxml_et

    # bs4
    if "bs4" not in sys.modules:
        # Try to import real bs4 first
        try:
            import bs4

            sys.modules["bs4"] = bs4
        except ImportError:
            bs4_mock = MagicMock()

            # Create a mock Tag class that can be used for isinstance checks
            class MockTag:
                def __init__(self, *args, **kwargs):
                    pass

                def get(self, key):
                    return None

            # Side effect for find/find_all to allow specific mocking in tests
            def find_side_effect(*args, **kwargs):
                return None

            bs4_instance = MagicMock()
            bs4_instance.find.side_effect = find_side_effect
            # Allow constructor to return our instance
            bs4_mock.BeautifulSoup.return_value = bs4_instance

            # Assign Tag class
            bs4_mock.Tag = MockTag

            sys.modules["bs4"] = bs4_mock
            sys.modules["bs4.BeautifulSoup"] = bs4_mock.BeautifulSoup
            sys.modules["bs4.Tag"] = MockTag
            sys.modules["bs4.element"] = MagicMock()
            sys.modules["bs4.element"].Tag = MockTag

    # dateutil
    if "dateutil" not in sys.modules:
        sys.modules["dateutil"] = MagicMock()
        sys.modules["dateutil.parser"] = MagicMock()

# Explicitly add keyring mock at end of file if not present (not great but works if global)
# Or define a fixture that patches sys.modules? No, config_manager imports it at module level.

# So we must patch sys.modules before config_manager is imported.
# conftest.py is imported first, so any code at top level runs.

if "keyring" not in sys.modules:
    import sys
    from unittest.mock import MagicMock

    keyring_mock = MagicMock()
    keyring_mock.get_password.return_value = None

    class MockPasswordDeleteError(Exception):
        pass

    keyring_mock.errors = MagicMock()
    keyring_mock.errors.PasswordDeleteError = MockPasswordDeleteError

    sys.modules["keyring"] = keyring_mock
    sys.modules["keyring.errors"] = keyring_mock.errors
