"""
Unit tests for the RateLimiter class.
"""

import time
import unittest

from rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_initial_burst(self):
        """Test that we can burst up to capacity initially."""
        # Rate 1.0, Capacity 3.0
        limiter = RateLimiter(rate=1.0, capacity=3.0)

        # Should allow 3 immediately
        self.assertTrue(limiter.check())
        self.assertTrue(limiter.check())
        self.assertTrue(limiter.check())

        # 4th should fail
        self.assertFalse(limiter.check())

    def test_refill(self):
        """Test that tokens refill over time."""
        # Rate 10.0 (fast refill), Capacity 1.0
        limiter = RateLimiter(rate=10.0, capacity=1.0)

        # Consume 1
        self.assertTrue(limiter.check())
        self.assertFalse(limiter.check())

        # Wait 0.15s (should refill ~1.5 tokens, capped at 1.0)
        time.sleep(0.15)

        # Should be able to consume again
        self.assertTrue(limiter.check())

    def test_rate_limit_enforcement(self):
        """Test that steady rate is enforced."""
        # Rate 2.0 (2 per sec), Capacity 1.0
        limiter = RateLimiter(rate=2.0, capacity=1.0)

        self.assertTrue(limiter.check())  # consume 1
        self.assertFalse(limiter.check())  # empty

        # Wait 0.25s (refill 0.5) -> 0.5 < 1.0 -> False
        time.sleep(0.25)
        self.assertFalse(limiter.check())

        # Wait another 0.3s (total 0.55s -> ~1.1 refill) -> True
        time.sleep(0.3)
        self.assertTrue(limiter.check())


if __name__ == "__main__":
    unittest.main()
