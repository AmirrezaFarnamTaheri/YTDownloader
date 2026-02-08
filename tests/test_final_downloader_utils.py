import pytest

from downloader.constants import RESERVED_FILENAMES


def test_constants_availability():
    """Verify that constants are correctly available in the new location."""
    assert "CON" in RESERVED_FILENAMES
    assert "PRN" in RESERVED_FILENAMES
    assert "NUL" in RESERVED_FILENAMES
    assert len(RESERVED_FILENAMES) > 0


def test_no_legacy_imports():
    """Verify that old import paths raise ImportError."""
    with pytest.raises(ImportError):
        import downloader.utils.constants
