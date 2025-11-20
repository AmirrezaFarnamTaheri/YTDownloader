"""
Unit tests for UI utility functions.
"""
import unittest
from ui_utils import validate_url, validate_proxy, validate_rate_limit, format_file_size

class TestUIUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def test_validate_url(self):
        self.assertTrue(validate_url("https://www.youtube.com/watch?v=test"))
        self.assertFalse(validate_url("ftp://test.com"))
        self.assertFalse(validate_url("short"))

    def test_validate_proxy(self):
        self.assertTrue(validate_proxy(""))
        self.assertTrue(validate_proxy("http://127.0.0.1:8080"))
        self.assertFalse(validate_proxy("invalid"))

    def test_validate_rate_limit(self):
        self.assertTrue(validate_rate_limit(""))
        self.assertTrue(validate_rate_limit("50K"))
        self.assertTrue(validate_rate_limit("10M"))
        self.assertFalse(validate_rate_limit("invalid"))

    def test_format_file_size(self):
        self.assertEqual(format_file_size(None), 'N/A')
        self.assertEqual(format_file_size(0), '0.00 B')
        self.assertEqual(format_file_size(1024), '1.00 KB')
        self.assertEqual(format_file_size(1048576), '1.00 MB')

if __name__ == '__main__':
    unittest.main()
