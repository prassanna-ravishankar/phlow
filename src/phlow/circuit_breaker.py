"""
Circuit breaker implementation for Phlow.

Provides fault tolerance for external dependencies by automatically
failing fast when services are degraded or unavailable.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .exceptions import CircuitBreakerError
from .monitoring import get_logger, get_metrics_collector


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 60.0  # Seconds before trying recovery
    expected_exception: type = Exception  # Exception type to count as failure
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Operation timeout in seconds


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Implements the circuit breaker pattern to prevent cascading failures
    when external dependencies are unavailable or degraded.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State tracking
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0  # For half-open state
        self.last_failure_time = 0.0

        # Monitoring
        self.logger = get_logger()
        self.metrics = get_metrics_collector()

    def _can_attempt(self) -> bool:
        """Check if we can attempt the operation."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self._transition_to_half_open()
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False

    def _on_success(self):
        """Handle successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()

    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state = CircuitBreakerState.OPEN
        self.success_count = 0
        self.logger.warning(
            f"Circuit breaker {self.name} opened",
            failure_count=self.failure_count,
            threshold=self.config.failure_threshold,
        )

        # Track metrics
        if hasattr(self.metrics, "record_circuit_breaker_state"):
            self.metrics.record_circuit_breaker_state(self.name, "open")

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self.logger.info(
            f"Circuit breaker {self.name} half-open (testing recovery)",
            recovery_timeout=self.config.recovery_timeout,
        )

        # Track metrics
        if hasattr(self.metrics, "record_circuit_breaker_state"):
            self.metrics.record_circuit_breaker_state(self.name, "half_open")

    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info(
            f"Circuit breaker {self.name} closed (recovered)",
            success_threshold=self.config.success_threshold,
        )

        # Track metrics
        if hasattr(self.metrics, "record_circuit_breaker_state"):
            self.metrics.record_circuit_breaker_state(self.name, "closed")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection (sync).

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from function
        """
        if not self._can_attempt():
            raise CircuitBreakerError(
                f"Circuit breaker {self.name} is OPEN. "
                f"Retry after {self.config.recovery_timeout} seconds."
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise e

    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from function
        """
        if not self._can_attempt():
            raise CircuitBreakerError(
                f"Circuit breaker {self.name} is OPEN. "
                f"Retry after {self.config.recovery_timeout} seconds."
            )

        try:
            # Add timeout to async operations
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.timeout
            )
            self._on_success()
            return result
        except (self.config.expected_exception, asyncio.TimeoutError) as e:
            self._on_failure()
            if isinstance(e, asyncio.TimeoutError):
                raise CircuitBreakerError(
                    f"Operation timed out after {self.config.timeout} seconds"
                ) from e
            raise e

    def __call__(self, func: Callable) -> Callable:
        """
        Use as decorator for function protection.

        Example:
            @circuit_breaker("external_api")
            def call_api():
                return requests.get("https://api.example.com")
        """
        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                return await self.acall(func, *args, **kwargs)

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)

            return sync_wrapper

    @property
    def stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
        }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Provides centralized management of circuit breakers for different
    external dependencies.
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self.logger = get_logger()

    def get_breaker(
        self, name: str, config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker.

        Args:
            name: Circuit breaker name
            config: Configuration (uses default if not provided)

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
            self.logger.info(f"Created circuit breaker: {name}")

        return self._breakers[name]

    def get_stats(self) -> dict[str, dict]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.stats for name, breaker in self._breakers.items()}

    def reset_breaker(self, name: str):
        """Reset a circuit breaker to CLOSED state."""
        if name in self._breakers:
            breaker = self._breakers[name]
            breaker.state = CircuitBreakerState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
            self.logger.info(f"Reset circuit breaker: {name}")

    def reset_all(self):
        """Reset all circuit breakers."""
        for name in self._breakers:
            self.reset_breaker(name)


# Global registry instance
_registry: CircuitBreakerRegistry | None = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    timeout: float = 30.0,
    expected_exception: type = Exception,
) -> Callable:
    """
    Decorator for circuit breaker protection.

    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before trying recovery
        timeout: Operation timeout for async functions
        expected_exception: Exception type to count as failure

    Returns:
        Decorated function with circuit breaker protection
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        timeout=timeout,
        expected_exception=expected_exception,
    )

    registry = get_circuit_breaker_registry()
    breaker = registry.get_breaker(name, config)

    return breaker


# Predefined circuit breakers for common Phlow dependencies
def supabase_circuit_breaker() -> CircuitBreaker:
    """Circuit breaker for Supabase operations."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        timeout=10.0,
        expected_exception=Exception,  # Catch all Supabase errors
    )
    registry = get_circuit_breaker_registry()
    return registry.get_breaker("supabase", config)


def did_resolution_circuit_breaker() -> CircuitBreaker:
    """Circuit breaker for DID resolution operations."""
    import httpx

    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        timeout=15.0,
        expected_exception=(httpx.HTTPError, asyncio.TimeoutError),
    )
    registry = get_circuit_breaker_registry()
    return registry.get_breaker("did_resolution", config)


def a2a_messaging_circuit_breaker() -> CircuitBreaker:
    """Circuit breaker for A2A messaging operations."""
    import httpx

    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=45.0,
        timeout=20.0,
        expected_exception=(httpx.HTTPError, asyncio.TimeoutError),
    )
    registry = get_circuit_breaker_registry()
    return registry.get_breaker("a2a_messaging", config)
