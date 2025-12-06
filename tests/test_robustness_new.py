# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
# pylint: disable=duplicate-code
"""
Robustness tests for utilities.
"""

import unittest
from unittest.mock import MagicMock, patch

from utils import CancelToken


class TestCancelToken(unittest.TestCase):

    def test_init(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        self.assertFalse(token.is_paused)

    def test_cancel_flow(self):
        token = CancelToken()
        token.cancel()
        self.assertTrue(token.cancelled)

    def test_check_raises(self):
        token = CancelToken()
        token.cancel()
        with self.assertRaises(Exception) as cm:
            token.check()
        # Case insensitive match or exact match
        # Message changed to "Download Cancelled by user" in Utils to match tasks.py expectation
        self.assertIn("Cancelled", str(cm.exception))

    def test_pause_resume(self):
        token = CancelToken()
        token.pause()
        self.assertTrue(token.is_paused)
        token.resume()
        self.assertFalse(token.is_paused)

    @patch("time.sleep")
    def test_pause_timeout(self, mock_sleep):
        token = CancelToken(pause_timeout=0.1)
        token.pause()

        # Simulate time passing
        with patch("time.time", side_effect=[100, 100.2, 100.3]):
            with self.assertRaises(RuntimeError) as cm:
                token.check()
            self.assertIn("too long", str(cm.exception))
