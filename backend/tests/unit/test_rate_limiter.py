"""Unit tests for app.api_gateway.rate_limiter — in-memory rate limiter."""

import time
import pytest
from app.api_gateway.rate_limiter import RateLimiter


@pytest.mark.unit
class TestRateLimiter:

    def test_within_limit(self):
        limiter = RateLimiter(rate=10, period=60)
        results = [limiter.is_allowed("user_1") for _ in range(10)]
        assert all(results) is True

    def test_exceed_limit(self):
        limiter = RateLimiter(rate=5, period=60)
        for _ in range(5):
            assert limiter.is_allowed("user_2") is True
        assert limiter.is_allowed("user_2") is False

    def test_different_keys_independent(self):
        limiter = RateLimiter(rate=3, period=60)
        for _ in range(3):
            assert limiter.is_allowed("key_a") is True
        assert limiter.is_allowed("key_a") is False
        # key_b should still have allowance
        assert limiter.is_allowed("key_b") is True
