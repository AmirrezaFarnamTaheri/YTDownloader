# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import re
import unittest


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
        for t in invalid_inputs:
            with self.subTest(t=t):
                self.assertFalse(self.time_pattern.match(t))


if __name__ == "__main__":
    unittest.main()
