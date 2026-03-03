"""
Tests for production-readiness hardening:

1. RBAC enforcement — all routes require auth, mutation routes require operator
2. CORS lockdown — origins loaded from config, not wildcard
3. System version endpoint
"""

import pytest
from fastapi.testclient import TestClient


# ─── Helpers ────────────────────────────────────────────────────


@pytest.fixture
def client():
    """Test client with app state initialized (DEMO_MODE=True by default)."""
    from backend.main import app
    from backend.brain.orchestrator import CommandBrain
    from backend.memory.store import MemoryStore
    from backend.telemetry.collector import TelemetryCollector

    app.state.brain = CommandBrain()
    app.state.memory = MemoryStore()
    app.state.telemetry = TelemetryCollector()
    app.state.brain.set_memory(app.state.memory)
    app.state.brain.set_telemetry(app.state.telemetry)

    return TestClient(app)


def _get_admin_token(client) -> str:
    """Issue a JWT for the admin user."""
    resp = client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _get_viewer_token(client) -> str:
    """Issue a JWT for the viewer-only user."""
    resp = client.post(
        "/api/v1/auth/token",
        json={"username": "viewer", "password": "viewer"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. RBAC — Read endpoints accessible with viewer token
# =====================================================================


class TestRBACViewerAccess:
    """All read (GET) endpoints should be accessible by a viewer."""

    def test_dashboard_overview(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/dashboard/overview", headers=_auth(token))
        assert resp.status_code == 200

    def test_agents_list(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/agents/", headers=_auth(token))
        assert resp.status_code == 200

    def test_workflows_list(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/workflows/", headers=_auth(token))
        assert resp.status_code == 200

    def test_telemetry_metrics(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/telemetry/metrics", headers=_auth(token))
        assert resp.status_code == 200

    def test_activity_feed(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/dashboard/activity", headers=_auth(token))
        assert resp.status_code == 200

    def test_learning_dashboard(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/dashboard/learning", headers=_auth(token))
        assert resp.status_code == 200

    def test_carbon_dashboard(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/dashboard/carbon", headers=_auth(token))
        assert resp.status_code == 200

    def test_approvals_pending(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/approvals/pending", headers=_auth(token))
        assert resp.status_code == 200

    def test_approvals_history(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/approvals/history", headers=_auth(token))
        assert resp.status_code == 200

    def test_explain_agent(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/explain/agent/sre", headers=_auth(token))
        assert resp.status_code == 200

    def test_demo_scenarios(self, client):
        token = _get_viewer_token(client)
        resp = client.get("/api/v1/workflows/demo/scenarios", headers=_auth(token))
        assert resp.status_code == 200


# =====================================================================
# 2. RBAC — Mutation endpoints blocked for viewer, allowed for operator
# =====================================================================


class TestRBACMutationEnforcement:
    """
    Mutation (POST) endpoints must reject viewer-only tokens (403)
    and accept operator/admin tokens (200).
    """

    def test_cancel_workflow_blocked_for_viewer(self, client):
        token = _get_viewer_token(client)
        resp = client.post(
            "/api/v1/workflows/fake-id/cancel",
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_cancel_workflow_allowed_for_admin(self, client):
        token = _get_admin_token(client)
        resp = client.post(
            "/api/v1/workflows/fake-id/cancel",
            headers=_auth(token),
        )
        # 200 or 404 — not 403
        assert resp.status_code in (200, 404)

    def test_test_trigger_blocked_for_viewer(self, client):
        token = _get_viewer_token(client)
        resp = client.post(
            "/api/v1/webhooks/test-trigger",
            json={"scenario": "pipeline_failure_missing_dep"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_test_trigger_allowed_for_admin(self, client):
        token = _get_admin_token(client)
        resp = client.post(
            "/api/v1/webhooks/test-trigger",
            json={"scenario": "pipeline_failure_missing_dep"},
            headers=_auth(token),
        )
        assert resp.status_code in (200, 404, 422)

    def test_demo_run_blocked_for_viewer(self, client):
        token = _get_viewer_token(client)
        resp = client.post(
            "/api/v1/workflows/demo/run/pipeline_failure_missing_dep",
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_demo_run_allowed_for_admin(self, client):
        token = _get_admin_token(client)
        resp = client.post(
            "/api/v1/workflows/demo/run/pipeline_failure_missing_dep",
            headers=_auth(token),
        )
        assert resp.status_code in (200, 404)

    def test_approval_approve_blocked_for_viewer(self, client):
        token = _get_viewer_token(client)
        resp = client.post(
            "/api/v1/approvals/fake-id/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_approval_reject_blocked_for_viewer(self, client):
        token = _get_viewer_token(client)
        resp = client.post(
            "/api/v1/approvals/fake-id/reject",
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_approval_approve_allowed_for_admin(self, client):
        token = _get_admin_token(client)
        resp = client.post(
            "/api/v1/approvals/fake-id/approve",
            headers=_auth(token),
        )
        # 404 = auth passed, just no such approval
        assert resp.status_code == 404

    def test_approval_reject_allowed_for_admin(self, client):
        token = _get_admin_token(client)
        resp = client.post(
            "/api/v1/approvals/fake-id/reject",
            headers=_auth(token),
        )
        assert resp.status_code == 404


# =====================================================================
# 3. RBAC — Production mode rejects unauthenticated requests
# =====================================================================


class TestRBACProductionReject:
    """In production mode (DEMO_MODE=False), unauthenticated requests are rejected."""

    def test_unauthenticated_rejected_in_production(self, client):
        from config import settings
        original_demo = settings.DEMO_MODE
        original_env = settings.APP_ENV
        settings.DEMO_MODE = False
        settings.APP_ENV = "production"
        try:
            resp = client.get("/api/v1/dashboard/overview")
            assert resp.status_code == 401
        finally:
            settings.DEMO_MODE = original_demo
            settings.APP_ENV = original_env

    def test_authenticated_works_in_production(self, client):
        from config import settings
        original_demo = settings.DEMO_MODE
        original_env = settings.APP_ENV
        settings.DEMO_MODE = False
        settings.APP_ENV = "production"
        try:
            token = _get_admin_token(client)
            resp = client.get("/api/v1/dashboard/overview", headers=_auth(token))
            assert resp.status_code == 200
        finally:
            settings.DEMO_MODE = original_demo
            settings.APP_ENV = original_env


# =====================================================================
# 4. CORS Lockdown
# =====================================================================


class TestCORSLockdown:
    """CORS origins should come from config, not wildcard *."""

    def test_cors_origins_from_config(self):
        from config import settings
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0
        assert "*" not in settings.CORS_ORIGINS

    def test_cors_allowed_origin(self, client):
        resp = client.options(
            "/api/v1/dashboard/overview",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should allow localhost:3000
        allow_origin = resp.headers.get("access-control-allow-origin", "")
        assert allow_origin == "http://localhost:3000"

    def test_cors_disallowed_origin(self, client):
        resp = client.options(
            "/api/v1/dashboard/overview",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should NOT return evil.com as allowed origin
        allow_origin = resp.headers.get("access-control-allow-origin", "")
        assert allow_origin != "http://evil.com"

    def test_main_does_not_use_wildcard(self):
        """Verify the CORS middleware is not configured with allow_origins=['*']."""
        from backend.main import app
        for mw in app.user_middleware:
            if "CORSMiddleware" in str(mw):
                kwargs = mw.kwargs
                origins = kwargs.get("allow_origins", [])
                assert origins != ["*"], "CORS should not use wildcard in production"


# =====================================================================
# 5. System Version Endpoint
# =====================================================================


class TestSystemVersionEndpoint:
    """GET /api/v1/system/version should return build + runtime info."""

    def test_version_returns_200(self, client):
        resp = client.get("/api/v1/system/version")
        assert resp.status_code == 200

    def test_version_has_required_fields(self, client):
        resp = client.get("/api/v1/system/version")
        data = resp.json()
        assert data["name"] == "AutoForge"
        assert "version" in data
        assert "git_sha" in data
        assert "python" in data
        assert "environment" in data
        assert "demo_mode" in data
        assert "capabilities" in data

    def test_version_lists_capabilities(self, client):
        data = client.get("/api/v1/system/version").json()
        caps = data["capabilities"]
        assert "multi_agent_orchestration" in caps
        assert "self_healing_pipelines" in caps
        assert "dag_execution" in caps
        assert "human_in_the_loop" in caps

    def test_version_lists_agents(self, client):
        data = client.get("/api/v1/system/version").json()
        agents = data["agents"]
        assert "sre" in agents
        assert "security" in agents
        assert len(agents) == 6


# =====================================================================
# 6. Auth Middleware Unit Tests
# =====================================================================


class TestAuthMiddleware:
    """Unit tests for auth middleware logic."""

    def test_require_role_returns_dependency(self):
        from middleware.auth import require_role
        dep = require_role("admin")
        assert callable(dep)

    def test_auth_context_has_role(self):
        from middleware.auth import AuthContext
        ctx = AuthContext(
            request_id="test",
            authenticated=True,
            roles=["admin", "viewer"],
        )
        assert ctx.has_role("admin")
        assert ctx.has_role("viewer")
        assert not ctx.has_role("operator")

    def test_jwt_roundtrip(self):
        from middleware.auth import _create_jwt, _verify_jwt
        token = _create_jwt("testuser", ["admin", "viewer"])
        claims = _verify_jwt(token)
        assert claims is not None
        assert claims["sub"] == "testuser"
        assert "admin" in claims["roles"]

    def test_invalid_jwt_rejected(self):
        from middleware.auth import _verify_jwt
        result = _verify_jwt("not-a-real-token")
        assert result is None
