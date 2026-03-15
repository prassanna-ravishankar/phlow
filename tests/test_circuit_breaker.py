"""Tests for circuit breaker module."""

import asyncio
import time

import pytest

from phlow.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitBreakerState,
)
from phlow.exceptions import CircuitBreakerError


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_allows_calls_when_closed(self):
        cb = CircuitBreaker("test")
        result = cb.call(lambda: 42)
        assert result == 42

    def test_opens_after_threshold(self):
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(self._failing_func)

        assert cb.state == CircuitBreakerState.OPEN

    def test_rejects_calls_when_open(self):
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60)
        cb = CircuitBreaker("test", config)

        with pytest.raises(ValueError):
            cb.call(self._failing_func)

        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: 42)

    def test_transitions_to_half_open_after_timeout(self):
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.05)
        cb = CircuitBreaker("test", config)

        with pytest.raises(ValueError):
            cb.call(self._failing_func)

        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.06)

        # Next call should be allowed (half-open)
        result = cb.call(lambda: "recovered")
        assert result == "recovered"

    def test_closes_after_success_threshold(self):
        config = CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=0.01, success_threshold=2
        )
        cb = CircuitBreaker("test", config)

        with pytest.raises(ValueError):
            cb.call(self._failing_func)

        time.sleep(0.02)

        cb.call(lambda: "ok")
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.call(lambda: "ok")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_reopens_on_failure_in_half_open(self):
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        cb = CircuitBreaker("test", config)

        with pytest.raises(ValueError):
            cb.call(self._failing_func)

        time.sleep(0.02)

        with pytest.raises(ValueError):
            cb.call(self._failing_func)

        assert cb.state == CircuitBreakerState.OPEN

    def test_resets_failure_count_on_success(self):
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)

        # Success should reset
        cb.call(lambda: "ok")
        assert cb.failure_count == 0

    def test_stats(self):
        cb = CircuitBreaker("test-stats")
        stats = cb.stats
        assert stats["name"] == "test-stats"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_async_call(self):
        cb = CircuitBreaker("async-test")
        result = await cb.acall(self._async_func)
        assert result == "async-ok"

    @pytest.mark.asyncio
    async def test_async_timeout(self):
        config = CircuitBreakerConfig(timeout=0.05)
        cb = CircuitBreaker("async-timeout", config)

        with pytest.raises(CircuitBreakerError, match="timed out"):
            await cb.acall(self._slow_async_func)

    def test_decorator_sync(self):
        cb = CircuitBreaker("decorator-test")

        @cb
        def guarded():
            return "decorated"

        assert guarded() == "decorated"

    @pytest.mark.asyncio
    async def test_decorator_async(self):
        cb = CircuitBreaker("decorator-async")

        @cb
        async def guarded():
            return "async-decorated"

        assert await guarded() == "async-decorated"

    @staticmethod
    def _failing_func():
        raise ValueError("boom")

    @staticmethod
    async def _async_func():
        return "async-ok"

    @staticmethod
    async def _slow_async_func():
        await asyncio.sleep(1)
        return "slow"


class TestCircuitBreakerRegistry:
    def test_creates_and_reuses_breakers(self):
        registry = CircuitBreakerRegistry()
        b1 = registry.get_breaker("svc")
        b2 = registry.get_breaker("svc")
        assert b1 is b2

    def test_different_names_different_breakers(self):
        registry = CircuitBreakerRegistry()
        b1 = registry.get_breaker("svc1")
        b2 = registry.get_breaker("svc2")
        assert b1 is not b2

    def test_get_stats(self):
        registry = CircuitBreakerRegistry()
        registry.get_breaker("a")
        registry.get_breaker("b")
        stats = registry.get_stats()
        assert "a" in stats
        assert "b" in stats

    def test_reset_breaker(self):
        registry = CircuitBreakerRegistry()
        cb = registry.get_breaker("svc", CircuitBreakerConfig(failure_threshold=1))
        with pytest.raises(ValueError):
            cb.call(TestCircuitBreaker._failing_func)
        assert cb.state == CircuitBreakerState.OPEN

        registry.reset_breaker("svc")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_reset_all(self):
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_breaker("s1", CircuitBreakerConfig(failure_threshold=1))
        cb2 = registry.get_breaker("s2", CircuitBreakerConfig(failure_threshold=1))

        with pytest.raises(ValueError):
            cb1.call(TestCircuitBreaker._failing_func)
        with pytest.raises(ValueError):
            cb2.call(TestCircuitBreaker._failing_func)

        registry.reset_all()
        assert cb1.state == CircuitBreakerState.CLOSED
        assert cb2.state == CircuitBreakerState.CLOSED
