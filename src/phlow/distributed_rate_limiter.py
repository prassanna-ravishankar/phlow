"""
Distributed rate limiting implementation for Phlow.

Provides Redis-backed rate limiting that works across multiple instances.
"""

import time
from typing import Protocol

try:
    import redis  # type: ignore
    from redis.exceptions import RedisError  # type: ignore

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

    # Create dummy classes for type hints
    class redis:  # type: ignore
        Redis = object

        @staticmethod
        def from_url(*args, **kwargs):  # type: ignore
            raise ImportError("Redis not available")

    class RedisError(Exception):
        pass


from .exceptions import RateLimitError


class RateLimitBackend(Protocol):
    """Protocol for rate limit storage backends."""

    def is_allowed(self, key: str, max_requests: int, window_ms: int) -> bool:
        """Check if request is allowed under rate limit."""
        ...

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        ...


class InMemoryRateLimitBackend:
    """
    In-memory rate limit backend (single instance only).

    This is the fallback when Redis is not available.
    """

    def __init__(self):
        self._buckets: dict[str, list[float]] = {}

    def is_allowed(self, key: str, max_requests: int, window_ms: int) -> bool:
        """Check if request is allowed using sliding window algorithm."""
        current_time = time.time() * 1000  # Convert to milliseconds
        window_start = current_time - window_ms

        # Get or create bucket
        if key not in self._buckets:
            self._buckets[key] = []

        # Remove expired entries
        self._buckets[key] = [
            timestamp for timestamp in self._buckets[key] if timestamp > window_start
        ]

        # Check if under limit
        if len(self._buckets[key]) >= max_requests:
            return False

        # Add current request
        self._buckets[key].append(current_time)
        return True

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._buckets:
            del self._buckets[key]


class RedisRateLimitBackend:
    """
    Redis-backed distributed rate limit backend.

    Uses Redis sorted sets for efficient sliding window rate limiting.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "phlow:ratelimit:",
    ):
        self.redis = redis_client
        self.key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"

    def is_allowed(self, key: str, max_requests: int, window_ms: int) -> bool:
        """
        Check if request is allowed using Redis sorted sets.

        This implements a sliding window algorithm that works across
        multiple instances.
        """
        redis_key = self._make_key(key)
        current_time = time.time() * 1000  # milliseconds
        window_start = current_time - window_ms

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # Count requests in current window
            pipe.zcard(redis_key)

            # Execute pipeline
            _, request_count = pipe.execute()

            # Check if under limit
            if request_count >= max_requests:
                return False

            # Add current request with score as timestamp
            # Use a unique member to handle concurrent requests
            import secrets

            member = f"{current_time}:{secrets.token_hex(4)}"
            self.redis.zadd(redis_key, {member: current_time})

            # Set expiry on the key (window + buffer)
            self.redis.expire(redis_key, int(window_ms / 1000) + 60)

            return True

        except RedisError:
            # If Redis fails, allow the request (fail open)
            # but log the error
            import logging

            logging.error("Redis rate limit check failed", exc_info=True)
            return True

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        redis_key = self._make_key(key)
        try:
            self.redis.delete(redis_key)
        except RedisError:
            pass  # Ignore errors on reset


class DistributedRateLimiter:
    """
    Distributed rate limiter with automatic fallback.

    Attempts to use Redis for distributed rate limiting, but falls back
    to in-memory limiting if Redis is not available.
    """

    def __init__(
        self,
        max_requests: int,
        window_ms: int,
        redis_url: str | None = None,
        backend: RateLimitBackend | None = None,
    ):
        """
        Initialize distributed rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the window
            window_ms: Time window in milliseconds
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            backend: Custom backend implementation (overrides redis_url)
        """
        self.max_requests = max_requests
        self.window_ms = window_ms

        if backend:
            self.backend = backend
        elif redis_url and REDIS_AVAILABLE:
            try:
                redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # Test connection
                redis_client.ping()
                self.backend = RedisRateLimitBackend(redis_client)
                import logging

                logging.info("Using Redis for distributed rate limiting")
            except Exception:
                import logging

                logging.warning(
                    "Failed to connect to Redis, falling back to in-memory rate limiting"
                )
                self.backend = InMemoryRateLimitBackend()
        else:
            if redis_url and not REDIS_AVAILABLE:
                import logging

                logging.warning(
                    "Redis URL provided but redis package not available, using in-memory rate limiting"
                )
            self.backend = InMemoryRateLimitBackend()

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if a request is allowed for the given identifier.

        Args:
            identifier: Unique identifier for rate limiting (e.g., user ID, IP)

        Returns:
            True if request is allowed, False otherwise
        """
        return self.backend.is_allowed(identifier, self.max_requests, self.window_ms)

    def check_and_raise(self, identifier: str) -> None:
        """
        Check rate limit and raise exception if exceeded.

        Args:
            identifier: Unique identifier for rate limiting

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        if not self.is_allowed(identifier):
            raise RateLimitError(
                f"Rate limit exceeded: {self.max_requests} requests per "
                f"{self.window_ms / 1000:.1f} seconds"
            )

    def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        self.backend.reset(identifier)


def create_rate_limiter_from_env(
    max_requests: int, window_ms: int, env_var: str = "REDIS_URL"
) -> DistributedRateLimiter:
    """
    Create a rate limiter using Redis URL from environment.

    Args:
        max_requests: Maximum requests in window
        window_ms: Window size in milliseconds
        env_var: Environment variable containing Redis URL

    Returns:
        DistributedRateLimiter instance
    """
    import os

    redis_url = os.environ.get(env_var)
    return DistributedRateLimiter(max_requests, window_ms, redis_url)
