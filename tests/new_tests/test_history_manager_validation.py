import unittest

from history_manager import HistoryManager


class TestHistoryManagerValidation(unittest.TestCase):
    def test_validate_input_edge_cases(self):
        """Test edge cases for input validation."""
        # Empty URL
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("", "Title", "path")

        # None URL
        with self.assertRaises(ValueError):
            HistoryManager._validate_input(None, "Title", "path")

        # Non-string URL
        with self.assertRaises(ValueError):
            HistoryManager._validate_input(123, "Title", "path")

        # URL too long
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("a" * 2049, "Title", "path")

        # Title too long
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://url", "a" * 501, "path")

        # Output path too long
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://url", "Title", "a" * 1025)

        # Null bytes
        with self.assertRaises(ValueError):
            HistoryManager._validate_input("http://url\x00", "Title", "path")


if __name__ == "__main__":
    unittest.main()
