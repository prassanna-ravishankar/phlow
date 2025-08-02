"""
Structured logging and monitoring for Phlow.

Provides centralized logging with structured output, metrics collection,
and integration with monitoring systems.
"""

import json
import logging
import time
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

try:
    import structlog  # type: ignore

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

# Context variables for request tracing
request_id: ContextVar[str | None] = ContextVar("request_id")
agent_id: ContextVar[str | None] = ContextVar("agent_id")


class PhlowStructuredLogger:
    """
    Structured logger for Phlow with context management.

    Provides consistent logging format with request tracing, metrics,
    and integration with external monitoring systems.
    """

    def __init__(
        self,
        logger_name: str = "phlow",
        log_level: str = "INFO",
        output_format: str = "json",  # json, console
        enable_metrics: bool = True,
        enable_tracing: bool = True,
    ):
        self.logger_name = logger_name
        self.enable_metrics = enable_metrics
        self.enable_tracing = enable_tracing

        if STRUCTLOG_AVAILABLE:
            # Configure structlog
            processors = [
                self._add_timestamp,
                self._add_context,
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
            ]

            if output_format == "json":
                processors.append(structlog.processors.JSONRenderer())
            else:
                processors.extend(
                    [
                        structlog.dev.ConsoleRenderer(colors=True),
                    ]
                )

            structlog.configure(
                processors=processors,
                wrapper_class=structlog.stdlib.BoundLogger,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )

            # Set up stdlib logger
            self.logger = structlog.get_logger(logger_name)
        else:
            # Fallback to standard logging
            self.logger = logging.getLogger(logger_name)

        logging.basicConfig(level=getattr(logging, log_level.upper()))

        # Metrics storage
        self._metrics: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _add_timestamp(logger, method_name, event_dict):
        """Add timestamp to log events."""
        event_dict["timestamp"] = time.time()
        return event_dict

    @staticmethod
    def _add_context(logger, method_name, event_dict):
        """Add request context to log events."""
        # Add request ID and agent ID from context
        if request_id.get():
            event_dict["request_id"] = request_id.get()
        if agent_id.get():
            event_dict["agent_id"] = agent_id.get()
        return event_dict

    def set_request_context(self, req_id: str | None = None, ag_id: str | None = None):
        """Set request context for logging."""
        if req_id:
            request_id.set(req_id)
        if ag_id:
            agent_id.set(ag_id)

    def generate_request_id(self) -> str:
        """Generate a new request ID and set it in context."""
        req_id = str(uuid4())
        request_id.set(req_id)
        return req_id

    def info(self, message: str, **kwargs):
        """Log info message with context."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info(message, **kwargs)
        else:
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.info(f"{message} {extra_info}".strip())

    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        if STRUCTLOG_AVAILABLE:
            self.logger.warning(message, **kwargs)
        else:
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.warning(f"{message} {extra_info}".strip())

    def error(self, message: str, **kwargs):
        """Log error message with context."""
        if STRUCTLOG_AVAILABLE:
            self.logger.error(message, **kwargs)
        else:
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.error(f"{message} {extra_info}".strip())

        # Track error metrics
        if self.enable_metrics:
            self._increment_metric(
                "errors", {"error_type": kwargs.get("error_type", "unknown")}
            )

    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        if STRUCTLOG_AVAILABLE:
            self.logger.debug(message, **kwargs)
        else:
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            self.logger.debug(f"{message} {extra_info}".strip())

    def log_authentication_event(
        self,
        agent_id: str,
        success: bool,
        token_hash: str | None = None,
        error: str | None = None,
        **metadata,
    ):
        """Log authentication events with structured data."""
        event_data = {
            "event_type": "authentication",
            "agent_id": agent_id,
            "success": success,
            "token_hash": token_hash,
            **metadata,
        }

        if error:
            event_data["error"] = error
            self.error("Authentication failed", **event_data)
        else:
            self.info("Authentication succeeded", **event_data)

        # Track metrics
        if self.enable_metrics:
            self._increment_metric("auth_attempts", {"success": success})

    def log_rate_limit_event(
        self,
        identifier: str,
        limit_type: str,
        exceeded: bool,
        current_count: int | None = None,
        limit: int | None = None,
    ):
        """Log rate limiting events."""
        event_data = {
            "event_type": "rate_limit",
            "identifier": identifier,
            "limit_type": limit_type,
            "exceeded": exceeded,
            "current_count": current_count,
            "limit": limit,
        }

        if exceeded:
            self.warning("Rate limit exceeded", **event_data)
        else:
            self.debug("Rate limit check", **event_data)

        # Track metrics
        if self.enable_metrics:
            self._increment_metric(
                "rate_limit_checks", {"limit_type": limit_type, "exceeded": exceeded}
            )

    def log_did_resolution_event(
        self,
        did: str,
        success: bool,
        cached: bool = False,
        duration_ms: float | None = None,
        error: str | None = None,
    ):
        """Log DID resolution events."""
        event_data = {
            "event_type": "did_resolution",
            "did": did,
            "success": success,
            "cached": cached,
            "duration_ms": duration_ms,
        }

        if error:
            event_data["error"] = error
            self.error("DID resolution failed", **event_data)
        else:
            self.info("DID resolution completed", **event_data)

        # Track metrics
        if self.enable_metrics:
            self._increment_metric(
                "did_resolutions", {"success": success, "cached": cached}
            )

    def log_database_event(
        self,
        operation: str,
        table: str,
        success: bool,
        duration_ms: float | None = None,
        error: str | None = None,
        **metadata,
    ):
        """Log database operations."""
        event_data = {
            "event_type": "database",
            "operation": operation,
            "table": table,
            "success": success,
            "duration_ms": duration_ms,
            **metadata,
        }

        if error:
            event_data["error"] = error
            self.error("Database operation failed", **event_data)
        else:
            self.debug("Database operation completed", **event_data)

        # Track metrics
        if self.enable_metrics:
            self._increment_metric(
                "database_operations",
                {"operation": operation, "table": table, "success": success},
            )

    def log_external_api_event(
        self,
        service: str,
        endpoint: str,
        method: str,
        status_code: int | None = None,
        duration_ms: float | None = None,
        success: bool = True,
        error: str | None = None,
    ):
        """Log external API calls."""
        event_data = {
            "event_type": "external_api",
            "service": service,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "success": success,
        }

        if error:
            event_data["error"] = error
            self.error("External API call failed", **event_data)
        else:
            self.info("External API call completed", **event_data)

        # Track metrics
        if self.enable_metrics:
            self._increment_metric(
                "external_api_calls",
                {"service": service, "success": success, "status_code": status_code},
            )

    def _increment_metric(self, metric_name: str, labels: dict[str, Any]):
        """Increment a metric counter."""
        if not self.enable_metrics:
            return

        if metric_name not in self._metrics:
            self._metrics[metric_name] = {}

        label_key = json.dumps(labels, sort_keys=True)
        if label_key not in self._metrics[metric_name]:
            self._metrics[metric_name][label_key] = 0

        self._metrics[metric_name][label_key] += 1

    def get_metrics(self) -> dict[str, dict[str, int]]:
        """Get current metrics."""
        return self._metrics.copy()

    def reset_metrics(self):
        """Reset all metrics."""
        self._metrics.clear()


class LoggingMiddleware:
    """
    Middleware for automatic request logging.

    Adds request tracing and automatic logging for FastAPI applications.
    """

    def __init__(self, logger: PhlowStructuredLogger):
        self.logger = logger

    async def __call__(self, request, call_next):
        """Process request with logging."""
        # Generate request ID
        self.logger.generate_request_id()

        # Extract agent ID from headers if available
        ag_id = request.headers.get("x-agent-id")
        if ag_id:
            self.logger.set_request_context(ag_id=ag_id)

        start_time = time.time()

        # Log request start
        self.logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log request completion
            self.logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log request error
            self.logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


# Global logger instance
_logger: PhlowStructuredLogger | None = None


def get_logger() -> PhlowStructuredLogger:
    """Get the global Phlow logger instance."""
    global _logger
    if _logger is None:
        _logger = PhlowStructuredLogger()
    return _logger


def configure_logging(
    log_level: str = "INFO",
    output_format: str = "json",
    enable_metrics: bool = True,
    enable_tracing: bool = True,
) -> PhlowStructuredLogger:
    """Configure global logging for Phlow."""
    global _logger
    _logger = PhlowStructuredLogger(
        log_level=log_level,
        output_format=output_format,
        enable_metrics=enable_metrics,
        enable_tracing=enable_tracing,
    )
    return _logger
