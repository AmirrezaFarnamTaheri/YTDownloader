import unittest
from unittest.mock import patch

from rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_init(self):
        """Test initialization of TokenBucket RateLimiter."""
        rl = RateLimiter(rate=2.0, capacity=5.0)
        self.assertEqual(rl._rate, 2.0)
        self.assertEqual(rl._capacity, 5.0)
        self.assertEqual(rl._tokens, 5.0)

    @patch("time.time")
    def test_check_allowed_burst(self, mock_time):
        """Test that burst requests are allowed up to capacity."""
        # Setup time before init
        mock_time.return_value = 100.0

        rl = RateLimiter(rate=1.0, capacity=2.0)

        # Should allow 2 immediate calls (burst)
        self.assertTrue(rl.check(cost=1.0))
        self.assertTrue(rl.check(cost=1.0))

        # 3rd call should fail (empty bucket)
        self.assertFalse(rl.check(cost=1.0))

    @patch("time.time")
    def test_check_refill(self, mock_time):
        """Test that tokens refill over time."""
        # Start at t=100
        mock_time.return_value = 100.0

        rl = RateLimiter(rate=1.0, capacity=1.0) # 1 token per second

        # Consume 1 (tokens -> 0)
        self.assertTrue(rl.check())
        self.assertFalse(rl.check())

        # Advance 0.5s -> 0.5 tokens (not enough for 1.0 cost)
        mock_time.return_value = 100.5
        self.assertFalse(rl.check())

        # Advance another 0.6s (total 1.1s) -> 1.0 tokens (capped at capacity)
        mock_time.return_value = 101.1
        self.assertTrue(rl.check())
