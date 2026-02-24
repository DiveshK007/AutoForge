"""
Tests for the enterprise improvements:
- Structured logging
- Middleware (auth, rate limiting, correlation)
- WebSocket hub
- Explain API
- API schemas
- Readiness probe
- Workflow types
- OpenTelemetry tracing
"""

import asyncio
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

# ─── Structured Logging Tests ─────────────────────────


class TestStructuredLogging:
    """Test the structlog configuration module."""

    def test_setup_logging_runs(self):
        from backend.logging_config import setup_logging
        setup_logging()  # Should not raise

    def test_get_logger_returns_bound_logger(self):
        from backend.logging_config import get_logger
        log = get_logger("test_module")
        assert log is not None

    def test_get_logger_name_binding(self):
        from backend.logging_config import get_logger
        log = get_logger("my_component")
        # Should have a bound 'component' key
        assert log is not None


# ─── Middleware: Correlation ID Tests ─────────────────


class TestCorrelationMiddleware:
    """Test the correlation ID middleware."""

    def test_middleware_import(self):
        from backend.middleware.correlation import CorrelationMiddleware
        assert CorrelationMiddleware is not None

    @pytest.mark.asyncio
    async def test_middleware_adds_request_id(self):
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from backend.middleware.correlation import CorrelationMiddleware

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/test")
            assert resp.status_code == 200
            assert "x-request-id" in resp.headers

    @pytest.mark.asyncio
    async def test_middleware_propagates_incoming_id(self):
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from backend.middleware.correlation import CorrelationMiddleware

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/test", headers={"X-Request-ID": "my-custom-id"})
            assert resp.headers["x-request-id"] == "my-custom-id"


# ─── Middleware: Rate Limiter Tests ───────────────────


class TestRateLimitMiddleware:
    """Test the token bucket rate limiter."""

    def test_middleware_import(self):
        from backend.middleware.rate_limiter import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self):
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from backend.middleware.rate_limiter import RateLimitMiddleware

        app = FastAPI()
        # Force enabled (override demo mode skip by passing enabled=True)
        app.add_middleware(RateLimitMiddleware, enabled=True)

        @app.get("/api/v1/dashboard/test")
        async def test_endpoint():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # In demo mode the middleware skips; test the middleware class directly
            # by patching settings.DEMO_MODE
            with patch("backend.middleware.rate_limiter.settings") as mock_settings:
                mock_settings.DEMO_MODE = False
                resp = await client.get("/api/v1/dashboard/test")
                assert resp.status_code == 200
                assert "x-ratelimit-limit" in resp.headers
                assert "x-ratelimit-remaining" in resp.headers


# ─── Middleware: Auth Tests ──────────────────────────


class TestAuthMiddleware:
    """Test the authentication middleware."""

    def test_auth_context_model(self):
        from backend.middleware.auth import AuthContext
        ctx = AuthContext(
            request_id="test-123",
            authenticated=True,
            auth_method="api_key",
            principal="test-user",
            roles=["viewer"],
        )
        assert ctx.authenticated is True
        assert ctx.principal == "test-user"
        assert "viewer" in ctx.roles

    def test_auth_context_has_role(self):
        from backend.middleware.auth import AuthContext
        ctx = AuthContext(
            request_id="test-123",
            authenticated=True,
            auth_method="api_key",
            principal="admin",
            roles=["admin", "viewer"],
        )
        assert ctx.has_role("admin") is True
        assert ctx.has_role("superadmin") is False


# ─── WebSocket Hub Tests ────────────────────────────


class TestWebSocketManager:
    """Test the WebSocket connection manager."""

    def test_manager_import(self):
        from backend.api.websocket import ws_manager
        assert ws_manager is not None

    def test_manager_initial_state(self):
        from backend.api.websocket import ConnectionManager
        mgr = ConnectionManager()
        assert mgr.active_count == 0
        assert mgr._broadcast_task is None

    @pytest.mark.asyncio
    async def test_broadcast_helpers(self):
        from backend.api.websocket import (
            broadcast_workflow_update,
            broadcast_agent_action,
            broadcast_activity,
        )
        # These should not raise even without active connections
        await broadcast_workflow_update("wf-1", "completed", {})
        await broadcast_agent_action("sre", "diagnose", "completed", 0.9)
        await broadcast_activity("test_event", "detail")


# ─── Explain API Tests ──────────────────────────────


class TestExplainAPI:
    """Test the explain endpoint."""

    def test_format_scenario_explanation(self):
        from backend.api.explain import _format_scenario_explanation
        tree = {
            "nodes": [
                {"id": "1", "label": "Pipeline Failed", "type": "event", "confidence": 0.9},
                {"id": "2", "label": "Analyzed logs", "type": "perception", "confidence": 0.85},
                {"id": "3", "label": "Missing dep", "type": "hypothesis", "confidence": 0.8},
            ],
            "edges": [
                {"source": "1", "target": "2"},
                {"source": "2", "target": "3"},
            ],
        }
        result = _format_scenario_explanation("pipeline_failure", tree)
        assert "Pipeline Failure" in result
        assert "Pipeline Failed" in result
        assert "Reasoning Explanation" in result

    def test_format_reasoning_explanation(self):
        from backend.api.explain import _format_reasoning_explanation
        chain = [
            {
                "type": "agent_execution",
                "agent": "sre",
                "decision": "fix missing dep",
                "detail": "Added numpy",
                "confidence": 0.9,
                "risk": 0.1,
                "wave": 1,
            },
        ]
        result = _format_reasoning_explanation(chain, ["sre"])
        assert "SRE" in result
        assert "fix missing dep" in result

    def test_format_reasoning_empty(self):
        from backend.api.explain import _format_reasoning_explanation
        result = _format_reasoning_explanation([], [])
        assert "No reasoning data" in result

    @pytest.mark.asyncio
    async def test_explain_workflow_demo_mode(self):
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from backend.api.explain import router
        from backend.brain.orchestrator import CommandBrain

        app = FastAPI()
        app.include_router(router, prefix="/explain")
        app.state.brain = CommandBrain()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Should work with a demo scenario alias
            resp = await client.get("/explain/workflow/pipeline_failure")
            assert resp.status_code == 200
            data = resp.json()
            assert "explanation" in data
            assert data["format"] == "markdown"


# ─── API Schema Validation Tests ─────────────────────


class TestAPISchemas:
    """Test Pydantic validation schemas."""

    def test_test_trigger_request_valid(self):
        from backend.models.api_schemas import TestTriggerRequest
        req = TestTriggerRequest(
            scenario="pipeline_failure_missing_dep",
            project_id="my-project",
        )
        assert req.scenario == "pipeline_failure_missing_dep"
        assert req.project_id == "my-project"

    def test_test_trigger_request_invalid_scenario(self):
        from backend.models.api_schemas import TestTriggerRequest
        with pytest.raises(Exception):
            TestTriggerRequest(scenario="nonexistent_scenario")

    def test_test_trigger_request_defaults(self):
        from backend.models.api_schemas import TestTriggerRequest
        req = TestTriggerRequest()
        assert req.project_id == "test-project"
        assert req.ref == "main"

    def test_health_response(self):
        from backend.models.api_schemas import HealthResponse
        resp = HealthResponse(version="1.0.0")
        assert resp.status == "operational"

    def test_readiness_response(self):
        from backend.models.api_schemas import ReadinessResponse
        resp = ReadinessResponse(
            ready=True,
            checks={"brain": True, "memory": True},
            version="1.0.0",
        )
        assert resp.ready is True

    def test_error_response(self):
        from backend.models.api_schemas import ErrorResponse
        resp = ErrorResponse(error="Not found", detail="Workflow xyz not found")
        assert resp.error == "Not found"

    def test_explain_response(self):
        from backend.models.api_schemas import ExplainResponse
        resp = ExplainResponse(
            workflow_id="wf-1",
            explanation="The SRE agent diagnosed...",
            reasoning_depth=12,
            confidence=0.92,
        )
        assert resp.confidence == 0.92


# ─── Readiness Probe Tests ──────────────────────────


class TestReadinessProbe:
    """Test the /ready endpoint."""

    @pytest.mark.asyncio
    async def test_ready_endpoint_returns_json(self):
        from httpx import AsyncClient, ASGITransport
        from backend.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/ready")
            # May be 200 or 503 depending on lifespan
            assert resp.status_code in (200, 503)
            data = resp.json()
            assert "ready" in data
            assert "checks" in data
            assert "version" in data


# ─── Workflow Type Tests ─────────────────────────────


class TestSecurityAlertWorkflow:
    """Test the security alert workflow."""

    def test_workflow_steps(self):
        from backend.workflows.security_alert import SecurityAlertWorkflow
        wf = SecurityAlertWorkflow()
        steps = wf.get_steps()
        assert len(steps) == 6
        agents = [s["agent"] for s in steps]
        assert "security" in agents
        assert "sre" in agents

    def test_matches_security_alert(self):
        from backend.workflows.security_alert import SecurityAlertWorkflow
        from backend.models.events import NormalizedEvent, EventType
        event = NormalizedEvent(
            event_type=EventType.SECURITY_ALERT,
            project_id="test",
        )
        assert SecurityAlertWorkflow.matches(event) is True

    def test_does_not_match_pipeline(self):
        from backend.workflows.security_alert import SecurityAlertWorkflow
        from backend.models.events import NormalizedEvent, EventType
        event = NormalizedEvent(
            event_type=EventType.PIPELINE_FAILURE,
            project_id="test",
        )
        assert SecurityAlertWorkflow.matches(event) is False


class TestMergeRequestWorkflow:
    """Test the merge request workflow."""

    def test_workflow_steps(self):
        from backend.workflows.merge_request import MergeRequestWorkflow
        wf = MergeRequestWorkflow()
        steps = wf.get_steps()
        assert len(steps) == 6
        agents = [s["agent"] for s in steps]
        assert "review" in agents
        assert "qa" in agents

    def test_matches_mr_opened(self):
        from backend.workflows.merge_request import MergeRequestWorkflow
        from backend.models.events import NormalizedEvent, EventType
        event = NormalizedEvent(
            event_type=EventType.MERGE_REQUEST_OPENED,
            project_id="test",
        )
        assert MergeRequestWorkflow.matches(event) is True

    def test_matches_mr_updated(self):
        from backend.workflows.merge_request import MergeRequestWorkflow
        from backend.models.events import NormalizedEvent, EventType
        event = NormalizedEvent(
            event_type=EventType.MERGE_REQUEST_UPDATED,
            project_id="test",
        )
        assert MergeRequestWorkflow.matches(event) is True


# ─── OpenTelemetry Tracing Tests ────────────────────


class TestTracing:
    """Test the OpenTelemetry tracing facade."""

    def test_tracer_import(self):
        from backend.telemetry.tracing import tracer
        assert tracer is not None

    def test_sync_span_no_error(self):
        from backend.telemetry.tracing import tracer
        with tracer.span("test_operation", {"key": "value"}):
            pass  # Should not raise

    @pytest.mark.asyncio
    async def test_async_span_no_error(self):
        from backend.telemetry.tracing import tracer
        async with tracer.async_span("test_async", {"key": "value"}):
            pass  # Should not raise

    def test_manual_span(self):
        from backend.telemetry.tracing import tracer
        span_id = tracer.start_span("manual_test")
        assert isinstance(span_id, str)
        tracer.end_span(span_id, status="ok")

    @pytest.mark.asyncio
    async def test_workflow_span(self):
        from backend.telemetry.tracing import tracer
        async with tracer.workflow_span("wf-123", "pipeline_failure"):
            pass

    @pytest.mark.asyncio
    async def test_agent_span(self):
        from backend.telemetry.tracing import tracer
        async with tracer.agent_span("sre", "diagnose", "wf-123"):
            pass


# ─── Config Improvements Tests ───────────────────────


class TestConfigImprovements:
    """Test the enhanced configuration."""

    def test_new_auth_settings(self):
        from backend.config import settings
        assert hasattr(settings, "API_KEYS")
        assert hasattr(settings, "JWT_SECRET")
        assert hasattr(settings, "JWT_ALGORITHM")
        assert hasattr(settings, "JWT_EXPIRE_MINUTES")

    def test_new_rate_limit_settings(self):
        from backend.config import settings
        assert hasattr(settings, "RATE_LIMIT_ENABLED")
        assert hasattr(settings, "RATE_LIMIT_DEFAULT_RPM")

    def test_new_otel_settings(self):
        from backend.config import settings
        assert hasattr(settings, "OTEL_ENABLED")
        assert hasattr(settings, "OTEL_EXPORTER_ENDPOINT")

    def test_is_production_property(self):
        from backend.config import settings
        assert settings.is_production is False  # default is development

    def test_all_api_keys_includes_secret(self):
        from backend.config import settings
        keys = settings.all_api_keys
        assert settings.SECRET_KEY in keys

    def test_all_api_keys_includes_demo(self):
        from backend.config import settings
        if settings.DEMO_MODE:
            assert "demo" in settings.all_api_keys


# ─── Workflows Package Tests ────────────────────────


class TestWorkflowsPackage:
    """Test the workflows package exports."""

    def test_package_exports(self):
        from backend.workflows import (
            PipelineFailureWorkflow,
            SecurityAlertWorkflow,
            MergeRequestWorkflow,
        )
        assert PipelineFailureWorkflow is not None
        assert SecurityAlertWorkflow is not None
        assert MergeRequestWorkflow is not None


# ─── Enhanced Main App Tests ─────────────────────────


class TestEnhancedMainApp:
    """Test the enhanced main.py with middleware stack."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from backend.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "operational"
            assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_has_correlation_id(self):
        from httpx import AsyncClient, ASGITransport
        from backend.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
            assert "x-request-id" in resp.headers

    @pytest.mark.asyncio
    async def test_health_has_rate_limit_headers(self):
        """Rate-limit headers appear when DEMO_MODE is off (on non-health paths)."""
        from unittest.mock import patch
        from httpx import AsyncClient, ASGITransport
        from backend.main import app
        import backend.middleware.rate_limiter as rl_mod

        original = rl_mod.settings.DEMO_MODE
        try:
            rl_mod.settings.DEMO_MODE = False
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # Use a non-health path so the rate limiter doesn't skip it
                resp = await client.get("/api/v1/dashboard/state")
                assert "x-ratelimit-limit" in resp.headers
        finally:
            rl_mod.settings.DEMO_MODE = original
