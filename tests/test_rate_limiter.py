"""Tests for rate limiting modules."""

import time

import pytest

from phlow.distributed_rate_limiter import (
    DistributedRateLimiter,
    InMemoryRateLimitBackend,
)
from phlow.exceptions import RateLimitError
from phlow.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_requests=3, window_ms=10_000)
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user1") is True

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_requests=2, window_ms=10_000)
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user1") is False

    def test_separate_identifiers(self):
        rl = RateLimiter(max_requests=1, window_ms=10_000)
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user2") is True
        assert rl.is_allowed("user1") is False

    def test_window_expiry(self):
        rl = RateLimiter(max_requests=1, window_ms=50)
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user1") is False
        time.sleep(0.06)
        assert rl.is_allowed("user1") is True

    def test_reset_specific(self):
        rl = RateLimiter(max_requests=1, window_ms=10_000)
        rl.is_allowed("user1")
        rl.reset("user1")
        assert rl.is_allowed("user1") is True

    def test_reset_all(self):
        rl = RateLimiter(max_requests=1, window_ms=10_000)
        rl.is_allowed("user1")
        rl.is_allowed("user2")
        rl.reset()
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user2") is True

    def test_check_and_raise_allows(self):
        rl = RateLimiter(max_requests=1, window_ms=10_000)
        rl.check_and_raise("user1")  # should not raise

    def test_check_and_raise_blocks(self):
        rl = RateLimiter(max_requests=1, window_ms=10_000)
        rl.is_allowed("user1")
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            rl.check_and_raise("user1")


class TestDistributedRateLimiter:
    def test_in_memory_fallback(self):
        rl = DistributedRateLimiter(max_requests=2, window_ms=10_000)
        assert isinstance(rl.backend, InMemoryRateLimitBackend)

    def test_allows_within_limit(self):
        rl = DistributedRateLimiter(max_requests=2, window_ms=10_000)
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user1") is True
        assert rl.is_allowed("user1") is False

    def test_check_and_raise(self):
        rl = DistributedRateLimiter(max_requests=1, window_ms=10_000)
        rl.is_allowed("user1")
        with pytest.raises(RateLimitError):
            rl.check_and_raise("user1")

    def test_reset(self):
        rl = DistributedRateLimiter(max_requests=1, window_ms=10_000)
        rl.is_allowed("user1")
        rl.reset("user1")
        assert rl.is_allowed("user1") is True

    def test_redis_url_without_redis_package(self):
        # Should fall back to in-memory when Redis URL given but no Redis available
        rl = DistributedRateLimiter(
            max_requests=10, window_ms=10_000, redis_url="redis://fake:6379"
        )
        assert isinstance(rl.backend, InMemoryRateLimitBackend)


class TestInMemoryRateLimitBackend:
    def test_sliding_window(self):
        backend = InMemoryRateLimitBackend()
        assert backend.is_allowed("k", 2, 10_000) is True
        assert backend.is_allowed("k", 2, 10_000) is True
        assert backend.is_allowed("k", 2, 10_000) is False

    def test_reset(self):
        backend = InMemoryRateLimitBackend()
        backend.is_allowed("k", 1, 10_000)
        backend.reset("k")
        assert backend.is_allowed("k", 1, 10_000) is True
