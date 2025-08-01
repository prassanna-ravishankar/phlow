"""Rate limiting utilities for Phlow authentication."""

import time
from threading import Lock
from typing import Dict, List, Optional


class RateLimiter:
    """In-memory rate limiter using sliding window algorithm."""

    def __init__(self, max_requests: int, window_ms: int):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed
            window_ms: Time window in milliseconds
        """
        self.max_requests = max_requests
        self.window_ms = window_ms
        self.requests: Dict[str, List[float]] = {}
        self._lock = Lock()

    def is_allowed(self, identifier: str) -> bool:
        """Check if a request is allowed for the given identifier.

        Args:
            identifier: Unique identifier (e.g., agent ID, IP address)

        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time() * 1000  # Convert to milliseconds

            # Get existing requests for this identifier
            if identifier not in self.requests:
                self.requests[identifier] = []

            request_times = self.requests[identifier]

            # Remove requests outside the time window
            cutoff = now - self.window_ms
            valid_requests = [t for t in request_times if t > cutoff]

            # Check if we can add another request
            if len(valid_requests) >= self.max_requests:
                self.requests[identifier] = valid_requests
                return False

            # Add current request and allow it
            valid_requests.append(now)
            self.requests[identifier] = valid_requests

            # Cleanup old entries periodically
            self._cleanup()

            return True

    def reset(self, identifier: Optional[str] = None) -> None:
        """Reset rate limit for a specific identifier or all identifiers.

        Args:
            identifier: Specific identifier to reset, or None to reset all
        """
        with self._lock:
            if identifier:
                self.requests.pop(identifier, None)
            else:
                self.requests.clear()

    def _cleanup(self) -> None:
        """Remove entries with no recent requests."""
        now = time.time() * 1000
        cutoff = now - self.window_ms

        # Remove identifiers with no recent requests
        to_remove = []
        for identifier, request_times in self.requests.items():
            if not request_times or max(request_times) <= cutoff:
                to_remove.append(identifier)

        for identifier in to_remove:
            del self.requests[identifier]
