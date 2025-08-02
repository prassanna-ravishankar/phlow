"""
Metrics collection and export for Phlow.

Provides Prometheus-compatible metrics for monitoring Phlow middleware
performance and security events.
"""

import time
from typing import Any

try:
    from prometheus_client import (  # type: ignore
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MetricsCollector:
    """
    Metrics collector with optional Prometheus integration.

    Collects performance and security metrics for monitoring and alerting.
    """

    def __init__(self, enable_prometheus: bool = False, registry: object | None = None):
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self.registry = registry or (
            CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        )

        # In-memory metrics storage (fallback when Prometheus not available)
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}

        # Initialize Prometheus metrics if available
        if self.enable_prometheus:
            self._init_prometheus_metrics()

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        if not PROMETHEUS_AVAILABLE:
            return

        # Authentication metrics
        self.auth_attempts_total = Counter(
            "phlow_auth_attempts_total",
            "Total number of authentication attempts",
            ["agent_id", "success"],
            registry=self.registry,
        )

        self.auth_duration_seconds = Histogram(
            "phlow_auth_duration_seconds",
            "Time spent on authentication",
            ["agent_id"],
            registry=self.registry,
        )

        # Rate limiting metrics
        self.rate_limit_checks_total = Counter(
            "phlow_rate_limit_checks_total",
            "Total number of rate limit checks",
            ["limit_type", "exceeded"],
            registry=self.registry,
        )

        # DID resolution metrics
        self.did_resolutions_total = Counter(
            "phlow_did_resolutions_total",
            "Total number of DID resolutions",
            ["cached", "success"],
            registry=self.registry,
        )

        self.did_resolution_duration_seconds = Histogram(
            "phlow_did_resolution_duration_seconds",
            "Time spent resolving DIDs",
            ["cached"],
            registry=self.registry,
        )

        # External API metrics
        self.external_api_calls_total = Counter(
            "phlow_external_api_calls_total",
            "Total number of external API calls",
            ["service", "status_code"],
            registry=self.registry,
        )

        self.external_api_duration_seconds = Histogram(
            "phlow_external_api_duration_seconds",
            "Time spent on external API calls",
            ["service"],
            registry=self.registry,
        )

        # Database metrics
        self.database_operations_total = Counter(
            "phlow_database_operations_total",
            "Total number of database operations",
            ["operation", "table", "success"],
            registry=self.registry,
        )

        self.database_operation_duration_seconds = Histogram(
            "phlow_database_operation_duration_seconds",
            "Time spent on database operations",
            ["operation", "table"],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_operations_total = Counter(
            "phlow_cache_operations_total",
            "Total number of cache operations",
            ["operation", "hit"],
            registry=self.registry,
        )

        # Active connections
        self.active_connections = Gauge(
            "phlow_active_connections",
            "Number of active connections",
            registry=self.registry,
        )

    def record_auth_attempt(
        self, agent_id: str, success: bool, duration_seconds: float
    ):
        """Record authentication attempt."""
        if self.enable_prometheus:
            self.auth_attempts_total.labels(
                agent_id=agent_id, success=str(success).lower()
            ).inc()
            self.auth_duration_seconds.labels(agent_id=agent_id).observe(
                duration_seconds
            )
        else:
            self._counters[f"auth_attempts_{agent_id}_{success}"] = (
                self._counters.get(f"auth_attempts_{agent_id}_{success}", 0) + 1
            )
            hist_key = f"auth_duration_{agent_id}"
            if hist_key not in self._histograms:
                self._histograms[hist_key] = []
            self._histograms[hist_key].append(duration_seconds)

    def record_rate_limit_check(self, limit_type: str, exceeded: bool):
        """Record rate limit check."""
        if self.enable_prometheus:
            self.rate_limit_checks_total.labels(
                limit_type=limit_type, exceeded=str(exceeded).lower()
            ).inc()
        else:
            key = f"rate_limit_checks_{limit_type}_{exceeded}"
            self._counters[key] = self._counters.get(key, 0) + 1

    def record_did_resolution(
        self, cached: bool, success: bool, duration_seconds: float
    ):
        """Record DID resolution."""
        if self.enable_prometheus:
            self.did_resolutions_total.labels(
                cached=str(cached).lower(), success=str(success).lower()
            ).inc()
            self.did_resolution_duration_seconds.labels(
                cached=str(cached).lower()
            ).observe(duration_seconds)
        else:
            key = f"did_resolutions_{cached}_{success}"
            self._counters[key] = self._counters.get(key, 0) + 1
            hist_key = f"did_resolution_duration_{cached}"
            if hist_key not in self._histograms:
                self._histograms[hist_key] = []
            self._histograms[hist_key].append(duration_seconds)

    def record_external_api_call(
        self, service: str, status_code: int, duration_seconds: float
    ):
        """Record external API call."""
        if self.enable_prometheus:
            self.external_api_calls_total.labels(
                service=service, status_code=str(status_code)
            ).inc()
            self.external_api_duration_seconds.labels(service=service).observe(
                duration_seconds
            )
        else:
            key = f"external_api_calls_{service}_{status_code}"
            self._counters[key] = self._counters.get(key, 0) + 1
            hist_key = f"external_api_duration_{service}"
            if hist_key not in self._histograms:
                self._histograms[hist_key] = []
            self._histograms[hist_key].append(duration_seconds)

    def record_database_operation(
        self, operation: str, table: str, success: bool, duration_seconds: float
    ):
        """Record database operation."""
        if self.enable_prometheus:
            self.database_operations_total.labels(
                operation=operation, table=table, success=str(success).lower()
            ).inc()
            self.database_operation_duration_seconds.labels(
                operation=operation, table=table
            ).observe(duration_seconds)
        else:
            key = f"database_operations_{operation}_{table}_{success}"
            self._counters[key] = self._counters.get(key, 0) + 1
            hist_key = f"database_operation_duration_{operation}_{table}"
            if hist_key not in self._histograms:
                self._histograms[hist_key] = []
            self._histograms[hist_key].append(duration_seconds)

    def record_cache_operation(self, operation: str, hit: bool):
        """Record cache operation."""
        if self.enable_prometheus:
            self.cache_operations_total.labels(
                operation=operation, hit=str(hit).lower()
            ).inc()
        else:
            key = f"cache_operations_{operation}_{hit}"
            self._counters[key] = self._counters.get(key, 0) + 1

    def set_active_connections(self, count: int):
        """Set number of active connections."""
        if self.enable_prometheus:
            self.active_connections.set(count)
        else:
            self._gauges["active_connections"] = float(count)

    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format."""
        if self.enable_prometheus:
            return generate_latest(self.registry).decode("utf-8")
        else:
            # Return simple text format for in-memory metrics
            lines = []

            # Counters
            for key, value in self._counters.items():
                lines.append(f"phlow_{key} {value}")

            # Gauges
            for key, value in self._gauges.items():
                lines.append(f"phlow_{key} {value}")

            # Histograms (simplified)
            for key, values in self._histograms.items():
                if values:
                    avg = sum(values) / len(values)
                    lines.append(f"phlow_{key}_avg {avg}")
                    lines.append(f"phlow_{key}_count {len(values)}")

            return "\n".join(lines)

    def get_metrics_dict(self) -> dict[str, Any]:
        """Get metrics as a dictionary."""
        metrics = {
            "counters": self._counters.copy(),
            "gauges": self._gauges.copy(),
        }

        # Add histogram stats
        histogram_stats = {}
        for key, values in self._histograms.items():
            if values:
                histogram_stats[key] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
        metrics["histograms"] = histogram_stats

        return metrics

    def reset_metrics(self):
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()
        self._gauges.clear()


class MetricsTimer:
    """Context manager for timing operations."""

    def __init__(self, metrics_collector: MetricsCollector, metric_name: str, **labels):
        self.metrics_collector = metrics_collector
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time

            # Record the timing based on metric type
            if self.metric_name == "auth":
                self.metrics_collector.record_auth_attempt(
                    agent_id=self.labels.get("agent_id", "unknown"),
                    success=exc_type is None,
                    duration_seconds=duration,
                )
            elif self.metric_name == "did_resolution":
                self.metrics_collector.record_did_resolution(
                    cached=self.labels.get("cached", False),
                    success=exc_type is None,
                    duration_seconds=duration,
                )
            elif self.metric_name == "external_api":
                self.metrics_collector.record_external_api_call(
                    service=self.labels.get("service", "unknown"),
                    status_code=self.labels.get("status_code", 0),
                    duration_seconds=duration,
                )
            elif self.metric_name == "database":
                self.metrics_collector.record_database_operation(
                    operation=self.labels.get("operation", "unknown"),
                    table=self.labels.get("table", "unknown"),
                    success=exc_type is None,
                    duration_seconds=duration,
                )


# Global metrics collector
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def configure_metrics(enable_prometheus: bool = False) -> MetricsCollector:
    """Configure global metrics collection."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(enable_prometheus=enable_prometheus)
    return _metrics_collector
