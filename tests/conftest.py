
import sys
import logging
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
        logger.warning(f"Flet import failed: {e}. Mocking flet for tests.")
        mock_flet()

def mock_flet():
    """Mocks the flet module in sys.modules."""
    flet_mock = MagicMock()

    # Define base classes for inheritance
    class MockControl:
        def __init__(self, *args, **kwargs):
            self.content = None
            self.controls = []
            self.value = None
            self.page = None

    class MockContainer(MockControl):
        pass

    class MockUserControl(MockControl):
        pass

    class MockView(MockControl):
        pass

    class MockPage(MockControl):
        platform = "linux"
        def launch_url(self, url): pass
        def update(self): pass

    # Assign classes to the mock
    flet_mock.Container = MockContainer
    flet_mock.UserControl = MockUserControl
    flet_mock.View = MockView
    flet_mock.Page = MockPage
    flet_mock.Control = MockControl

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

    # Mock colors and icons
    flet_mock.colors = MagicMock()
    flet_mock.icons = MagicMock()

    # Mock other controls as factories (MagicMock will handle calling them)
    # But for isinstance checks, they are classes on the mock.
    # Since MagicMock attributes are MagicMocks, and MagicMock() returns a MagicMock,
    # instantiating ft.Text() works.

    # Replace in sys.modules
    sys.modules["flet"] = flet_mock

    # Also ensure flet.auth and other submodules don't crash if imported
    sys.modules["flet.auth"] = MagicMock()
    sys.modules["flet.security"] = MagicMock()
