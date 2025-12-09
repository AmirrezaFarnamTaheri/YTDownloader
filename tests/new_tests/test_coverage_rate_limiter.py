import unittest
from unittest.mock import patch
from rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_init(self):
        rl = RateLimiter(limit_seconds=2.0)
        self.assertEqual(rl._limit_seconds, 2.0)
        self.assertEqual(rl._last_action_time, 0.0)

    @patch("time.time")
    def test_check_allowed(self, mock_time):
        rl = RateLimiter(limit_seconds=1.0)
        mock_time.return_value = 10.0
        self.assertTrue(rl.check())

        mock_time.return_value = 11.5
        self.assertTrue(rl.check())

    @patch("time.time")
    def test_check_limited(self, mock_time):
        rl = RateLimiter(limit_seconds=1.0)
        mock_time.return_value = 10.0
        rl.check()

        mock_time.return_value = 10.5
        self.assertFalse(rl.check())
