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

            # Handle positional args for controls list (common in Row, Column, ListView)
            if not self.controls and args and isinstance(args[0], list):
                self.controls = args[0]

            # Allow any other attribute to be set
            for k, v in kwargs.items():
                setattr(self, k, v)

        def update(self):
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

    # Assign classes to the mock
    flet_mock.Container = MockContainer
    flet_mock.UserControl = MockUserControl
    flet_mock.View = MockView
    flet_mock.Page = MockPage
    flet_mock.Control = MockControl
    flet_mock.SnackBar = MockSnackBar
    flet_mock.Text = MockText
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

    # Mock colors and icons
    flet_mock.colors = MagicMock()
    flet_mock.icons = MagicMock()

    # Replace in sys.modules
    sys.modules["flet"] = flet_mock
    # Also ensure flet.auth and other submodules don't crash if imported
    sys.modules["flet.auth"] = MagicMock()
    sys.modules["flet.security"] = MagicMock()

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

            class MockTag:
                pass

            bs4_mock.Tag = MockTag
            bs4_mock.BeautifulSoup = MagicMock()

            sys.modules["bs4"] = bs4_mock
            sys.modules["bs4.BeautifulSoup"] = bs4_mock.BeautifulSoup
            sys.modules["bs4.Tag"] = MockTag
            # Also mock element submodule
            sys.modules["bs4.element"] = MagicMock()
            sys.modules["bs4.element"].Tag = MockTag

    # dateutil
    if "dateutil" not in sys.modules:
        sys.modules["dateutil"] = MagicMock()
        sys.modules["dateutil.parser"] = MagicMock()
