import time
from unittest.mock import patch

import pytest

from utils import CancelToken


def test_cancel_token_pause_timeout():
    """Test that check raises exception after pause timeout."""
    token = CancelToken(pause_timeout=0.1)
    token.pause()

    with pytest.raises(Exception) as exc_info:
        token.check()
    assert "Download paused for too long" in str(exc_info.value)


def test_cancel_token_check_cancelled_during_pause():
    """Test that check notices cancellation while paused."""
    token = CancelToken()
    token.pause()

    # Run check in a thread or simulate it
    # We can patch time.sleep to trigger cancel

    def side_effect(seconds):
        token.cancel()

    with patch("time.sleep", side_effect=side_effect):
        with pytest.raises(Exception) as exc_info:
            token.check()
        assert "Download cancelled by user" in str(exc_info.value)
