
import unittest
import os
import signal
from unittest.mock import patch, MagicMock
from utils_shared import timeout_manager

class TestUtilsShared(unittest.TestCase):
    def test_timeout_manager_windows(self):
        with patch("os.name", "nt"):
            with timeout_manager(seconds=1):
                pass

    def test_timeout_manager_unix_success(self):
        with patch("os.name", "posix"), \
             patch("signal.signal") as mock_signal, \
             patch("signal.alarm") as mock_alarm:

            with timeout_manager(seconds=5):
                pass

            mock_alarm.assert_any_call(5)
            mock_alarm.assert_any_call(0)

    def test_timeout_manager_unix_timeout(self):
        with patch("os.name", "posix"), \
             patch("signal.signal") as mock_signal, \
             patch("signal.alarm") as mock_alarm:

            handler_ref = []
            def side_effect(sig, handler):
                if sig == signal.SIGALRM:
                    handler_ref.append(handler)
                return MagicMock()

            mock_signal.side_effect = side_effect

            try:
                with timeout_manager(seconds=1, error_message="Timed out"):
                    if handler_ref:
                        handler_ref[0](signal.SIGALRM, None)
            except TimeoutError as e:
                self.assertEqual(str(e), "Timed out")
