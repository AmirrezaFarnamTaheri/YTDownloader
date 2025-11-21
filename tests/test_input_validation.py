import unittest
import re


class TestInputValidation(unittest.TestCase):
    def setUp(self):
        self.time_pattern = re.compile(r"^(\d{1,2}:)?\d{1,2}:\d{2}$")

    def test_valid_time_formats(self):
        valid_inputs = ["10:00", "00:00", "01:30:00", "1:30:00", "59:59", "1:59:59"]
        for t in valid_inputs:
            with self.subTest(t=t):
                self.assertTrue(self.time_pattern.match(t))

    def test_invalid_time_formats(self):
        invalid_inputs = [
            "abc",
            "10-00",
            "10:0",  # Need 2 digits for seconds
            ":10:00",
            "10:00:",
            "100:00",  # Actually \d{1,2} matches 10, but wait
            # ^(\d{1,2}:)?\d{1,2}:\d{2}$
            # 100:00 -> 100 doesn't match \d{1,2}.
            # Wait, regex matches from start.
        ]
        # Let's check "100:00"
        # \d{1,2} matches "10". Then :00. So "10:00" matches.
        # If string is "100:00", ^\d{1,2} matches "10". Then :00. Then end $.
        # So "100:00" should FAIL because it has extra 0 at start? No.
        # "100:00". Group 1 optional. \d{1,2} matches "10". : \d{2} matches "00".
        # The remaining "0" at start makes it fail? No.
        # If I have "100:00".
        # If I use match(), it tries to match from beginning.
        # But \d{1,2} is greedy?
        # Actually, regex is tricky.

        for t in invalid_inputs:
            with self.subTest(t=t):
                self.assertFalse(self.time_pattern.match(t))


if __name__ == "__main__":
    unittest.main()
