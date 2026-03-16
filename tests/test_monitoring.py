"""Tests for monitoring module (logger and metrics)."""

import logging
from unittest.mock import MagicMock

import pytest

from phlow.monitoring.logger import (
    LoggingMiddleware,
    PhlowStructuredLogger,
    configure_logging,
    get_logger,
)
from phlow.monitoring.metrics import (
    MetricsCollector,
    MetricsTimer,
    configure_metrics,
    get_metrics_collector,
)


class TestPhlowStructuredLogger:
    def test_creates_with_defaults(self):
        logger = PhlowStructuredLogger()
        assert logger.logger_name == "phlow"
        assert logger.enable_metrics is True
        assert logger.enable_tracing is True

    def test_info_logging(self, caplog):
        logger = PhlowStructuredLogger(log_level="INFO")
        with caplog.at_level(logging.INFO, logger="phlow"):
            logger.info("test message", key="value")

    def test_warning_logging(self, caplog):
        logger = PhlowStructuredLogger(log_level="WARNING")
        with caplog.at_level(logging.WARNING, logger="phlow"):
            logger.warning("test warning", key="value")

    def test_error_logging_tracks_metrics(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.error("something broke", error_type="test_error")
        metrics = logger.get_metrics()
        assert "errors" in metrics

    def test_debug_logging(self, caplog):
        logger = PhlowStructuredLogger(log_level="DEBUG")
        with caplog.at_level(logging.DEBUG, logger="phlow"):
            logger.debug("debug msg", detail="x")

    def test_set_request_context(self):
        logger = PhlowStructuredLogger()
        logger.set_request_context(req_id="req-123", ag_id="agent-456")
        # Context is set via contextvars — no direct assertion needed
        # but verify it doesn't raise

    def test_generate_request_id(self):
        logger = PhlowStructuredLogger()
        req_id = logger.generate_request_id()
        assert len(req_id) > 0
        # Should be a UUID
        assert "-" in req_id

    def test_log_authentication_event_success(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_authentication_event(
            agent_id="agent-1", success=True, token_hash="abc123"
        )
        metrics = logger.get_metrics()
        assert "auth_attempts" in metrics

    def test_log_authentication_event_failure(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_authentication_event(
            agent_id="agent-1", success=False, token_hash="abc", error="expired"
        )
        metrics = logger.get_metrics()
        assert "auth_attempts" in metrics

    def test_log_rate_limit_event_exceeded(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_rate_limit_event(
            identifier="user-1",
            limit_type="auth",
            exceeded=True,
            current_count=11,
            limit=10,
        )
        metrics = logger.get_metrics()
        assert "rate_limit_checks" in metrics

    def test_log_rate_limit_event_allowed(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_rate_limit_event(
            identifier="user-1", limit_type="auth", exceeded=False
        )

    def test_log_did_resolution_event_success(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_did_resolution_event(
            did="did:web:example.com", success=True, cached=False, duration_ms=50.0
        )
        metrics = logger.get_metrics()
        assert "did_resolutions" in metrics

    def test_log_did_resolution_event_failure(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_did_resolution_event(
            did="did:web:example.com", success=False, error="timeout"
        )

    def test_log_database_event_success(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_database_event(
            operation="insert", table="agents", success=True, duration_ms=5.0
        )
        metrics = logger.get_metrics()
        assert "database_operations" in metrics

    def test_log_database_event_failure(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_database_event(
            operation="select",
            table="agents",
            success=False,
            error="connection_refused",
        )

    def test_log_external_api_event_success(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_external_api_event(
            service="did_resolver",
            endpoint="/resolve",
            method="GET",
            status_code=200,
            duration_ms=100.0,
        )
        metrics = logger.get_metrics()
        assert "external_api_calls" in metrics

    def test_log_external_api_event_failure(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_external_api_event(
            service="did_resolver",
            endpoint="/resolve",
            method="GET",
            success=False,
            error="timeout",
        )

    def test_metrics_disabled(self):
        logger = PhlowStructuredLogger(enable_metrics=False)
        logger.error("err", error_type="test")
        assert logger.get_metrics() == {}

    def test_reset_metrics(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.error("err", error_type="test")
        assert len(logger.get_metrics()) > 0
        logger.reset_metrics()
        assert logger.get_metrics() == {}

    def test_increment_metric_accumulates(self):
        logger = PhlowStructuredLogger(enable_metrics=True)
        logger.log_authentication_event("a1", success=True)
        logger.log_authentication_event("a2", success=True)
        metrics = logger.get_metrics()
        # Find the success=true metric
        for key, count in metrics["auth_attempts"].items():
            if "true" in key.lower():
                assert count == 2


class TestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_logs_request_lifecycle(self):
        logger = PhlowStructuredLogger()
        middleware = LoggingMiddleware(logger)

        request = MagicMock()
        request.method = "GET"
        request.url = "http://test.com/api"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}

        response = MagicMock()
        response.status_code = 200

        async def call_next(req):
            return response

        result = await middleware(request, call_next)
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_request_error(self):
        logger = PhlowStructuredLogger()
        middleware = LoggingMiddleware(logger)

        request = MagicMock()
        request.method = "POST"
        request.url = "http://test.com/api"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}

        async def call_next(req):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await middleware(request, call_next)

    @pytest.mark.asyncio
    async def test_extracts_agent_id_header(self):
        logger = PhlowStructuredLogger()
        middleware = LoggingMiddleware(logger)

        request = MagicMock()
        request.method = "GET"
        request.url = "http://test.com/api"
        request.client = None
        request.headers = {"x-agent-id": "agent-99"}

        response = MagicMock()
        response.status_code = 200

        async def call_next(req):
            return response

        await middleware(request, call_next)


class TestGetLoggerAndConfigure:
    def test_get_logger_returns_singleton(self):
        l1 = get_logger()
        l2 = get_logger()
        assert l1 is l2

    def test_configure_logging(self):
        logger = configure_logging(log_level="DEBUG", enable_metrics=False)
        assert isinstance(logger, PhlowStructuredLogger)
        assert logger.enable_metrics is False


class TestMetricsCollector:
    def test_record_auth_attempt(self):
        mc = MetricsCollector()
        mc.record_auth_attempt("agent-1", True, 0.05)
        assert mc._counters["auth_attempts_agent-1_True"] == 1

    def test_record_rate_limit_check(self):
        mc = MetricsCollector()
        mc.record_rate_limit_check("auth", False)
        assert mc._counters["rate_limit_checks_auth_False"] == 1

    def test_record_did_resolution(self):
        mc = MetricsCollector()
        mc.record_did_resolution(cached=False, success=True, duration_seconds=0.1)
        assert mc._counters["did_resolutions_False_True"] == 1
        assert len(mc._histograms["did_resolution_duration_False"]) == 1

    def test_record_external_api_call(self):
        mc = MetricsCollector()
        mc.record_external_api_call("supabase", 200, 0.05)
        assert mc._counters["external_api_calls_supabase_200"] == 1

    def test_record_database_operation(self):
        mc = MetricsCollector()
        mc.record_database_operation("insert", "agents", True, 0.01)
        assert mc._counters["database_operations_insert_agents_True"] == 1

    def test_record_cache_operation(self):
        mc = MetricsCollector()
        mc.record_cache_operation("get", True)
        assert mc._counters["cache_operations_get_True"] == 1

    def test_set_active_connections(self):
        mc = MetricsCollector()
        mc.set_active_connections(5)
        assert mc._gauges["active_connections"] == 5.0

    def test_get_metrics_text(self):
        mc = MetricsCollector()
        mc.record_auth_attempt("a1", True, 0.1)
        mc.set_active_connections(3)
        text = mc.get_metrics_text()
        assert "phlow_auth_attempts_a1_True" in text
        assert "phlow_active_connections" in text

    def test_get_metrics_dict(self):
        mc = MetricsCollector()
        mc.record_auth_attempt("a1", True, 0.1)
        d = mc.get_metrics_dict()
        assert "counters" in d
        assert "gauges" in d
        assert "histograms" in d

    def test_get_metrics_dict_histogram_stats(self):
        mc = MetricsCollector()
        mc.record_auth_attempt("a1", True, 0.1)
        mc.record_auth_attempt("a1", True, 0.3)
        d = mc.get_metrics_dict()
        hist = d["histograms"]["auth_duration_a1"]
        assert hist["count"] == 2
        assert hist["min"] == 0.1
        assert hist["max"] == 0.3
        assert 0.1 < hist["avg"] < 0.3

    def test_reset_metrics(self):
        mc = MetricsCollector()
        mc.record_auth_attempt("a1", True, 0.1)
        mc.set_active_connections(5)
        mc.reset_metrics()
        assert mc._counters == {}
        assert mc._gauges == {}
        assert mc._histograms == {}


class TestMetricsTimer:
    def test_auth_timer(self):
        mc = MetricsCollector()
        with MetricsTimer(mc, "auth", agent_id="a1"):
            pass
        assert "auth_attempts_a1_True" in mc._counters

    def test_auth_timer_on_failure(self):
        mc = MetricsCollector()
        with pytest.raises(ValueError):
            with MetricsTimer(mc, "auth", agent_id="a1"):
                raise ValueError("fail")
        assert "auth_attempts_a1_False" in mc._counters

    def test_database_timer(self):
        mc = MetricsCollector()
        with MetricsTimer(mc, "database", operation="select", table="agents"):
            pass
        assert "database_operations_select_agents_True" in mc._counters

    def test_external_api_timer(self):
        mc = MetricsCollector()
        with MetricsTimer(mc, "external_api", service="resolver", status_code=200):
            pass
        # MetricsTimer passes status_code from labels, which defaults to 0 in the timer
        # The timer reads labels.get("status_code", 0) for the record call
        assert "external_api_calls_resolver_200" in mc._counters

    def test_did_resolution_timer(self):
        mc = MetricsCollector()
        with MetricsTimer(mc, "did_resolution", cached=False):
            pass
        assert "did_resolutions_False_True" in mc._counters


class TestGetMetricsCollectorAndConfigure:
    def test_get_metrics_collector_returns_singleton(self):
        mc1 = get_metrics_collector()
        mc2 = get_metrics_collector()
        assert mc1 is mc2

    def test_configure_metrics(self):
        mc = configure_metrics(enable_prometheus=False)
        assert isinstance(mc, MetricsCollector)
        assert mc.enable_prometheus is False
