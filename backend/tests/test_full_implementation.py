"""
Tests for full-implementation features:
1. Database persistence layer (SQLAlchemy models, repository, Redis cache)
2. Real JWT authentication (token creation, verification, endpoint)
3. Celery worker dispatch (webhook → Celery routing)
4. Retry history API endpoint
5. Agent communication API endpoint
6. Auth token endpoint
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock


def _make_test_client():
    """Create a TestClient with app.state properly initialised (mirrors lifespan)."""
    from fastapi.testclient import TestClient
    from main import app
    from brain.orchestrator import CommandBrain
    from memory.store import MemoryStore
    from telemetry.collector import TelemetryCollector

    app.state.brain = CommandBrain()
    app.state.memory = MemoryStore()
    app.state.telemetry = TelemetryCollector()
    app.state.brain.set_memory(app.state.memory)
    app.state.brain.set_telemetry(app.state.telemetry)
    return TestClient(app)

# ─── 1. Database Layer Tests ────────────────────────────────────────────


class TestDatabaseEngine:
    """Test db/engine.py module."""

    def test_base_class_exists(self):
        from db.engine import Base
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "__subclasses__")

    def test_build_url_converts_postgresql(self):
        from db.engine import _build_url
        with patch("db.engine.settings") as mock_settings:
            mock_settings.DATABASE_URL = "postgresql://user:pass@host:5432/db"
            url = _build_url()
            assert url.startswith("postgresql+asyncpg://")

    def test_build_url_passthrough(self):
        from db.engine import _build_url
        with patch("db.engine.settings") as mock_settings:
            mock_settings.DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"
            url = _build_url()
            assert url == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_get_engine_creates_engine(self):
        """Engine factory should return an engine object."""
        from db import engine as engine_mod
        # Reset state
        engine_mod._engine = None
        engine_mod._session_factory = None
        try:
            eng = engine_mod.get_engine()
            assert eng is not None
            # Calling again returns same instance
            assert engine_mod.get_engine() is eng
        finally:
            engine_mod._engine = None
            engine_mod._session_factory = None

    def test_get_session_factory(self):
        from db import engine as engine_mod
        engine_mod._engine = None
        engine_mod._session_factory = None
        try:
            factory = engine_mod.get_session_factory()
            assert factory is not None
            assert engine_mod.get_session_factory() is factory
        finally:
            engine_mod._engine = None
            engine_mod._session_factory = None


class TestDatabaseTables:
    """Test db/tables.py ORM models."""

    def test_experience_row_table_name(self):
        from db.tables import ExperienceRow
        assert ExperienceRow.__tablename__ == "experiences"

    def test_experience_row_columns(self):
        from db.tables import ExperienceRow
        cols = {c.name for c in ExperienceRow.__table__.columns}
        expected = {"id", "agent_type", "failure_type", "context_summary",
                    "action_taken", "outcome", "success", "confidence",
                    "fix_time_seconds", "reusable_skill", "created_at"}
        assert expected.issubset(cols)

    def test_skill_row_table_name(self):
        from db.tables import SkillRow
        assert SkillRow.__tablename__ == "skills"

    def test_skill_row_columns(self):
        from db.tables import SkillRow
        cols = {c.name for c in SkillRow.__table__.columns}
        assert {"id", "name", "agent_type", "usage_count", "success_count"}.issubset(cols)

    def test_workflow_row_table_name(self):
        from db.tables import WorkflowRow
        assert WorkflowRow.__tablename__ == "workflows"

    def test_workflow_row_has_retry_history(self):
        """WorkflowRow should have a retry_history JSONB column."""
        from db.tables import WorkflowRow
        cols = {c.name for c in WorkflowRow.__table__.columns}
        assert "retry_history" in cols

    def test_workflow_row_has_shared_context(self):
        from db.tables import WorkflowRow
        cols = {c.name for c in WorkflowRow.__table__.columns}
        assert "shared_context" in cols

    def test_workflow_task_row_table_name(self):
        from db.tables import WorkflowTaskRow
        assert WorkflowTaskRow.__tablename__ == "workflow_tasks"

    def test_workflow_task_row_has_dependencies(self):
        from db.tables import WorkflowTaskRow
        cols = {c.name for c in WorkflowTaskRow.__table__.columns}
        assert "dependencies" in cols

    def test_policy_event_row_table_name(self):
        from db.tables import PolicyEventRow
        assert PolicyEventRow.__tablename__ == "policy_events"

    def test_policy_event_row_columns(self):
        from db.tables import PolicyEventRow
        cols = {c.name for c in PolicyEventRow.__table__.columns}
        assert {"id", "event_kind", "action", "reason", "agent_type", "approved_by", "created_at"}.issubset(cols)

    def test_workflow_row_tasks_relationship(self):
        from db.tables import WorkflowRow
        assert hasattr(WorkflowRow, "tasks")


class TestDatabaseRepository:
    """Test db/repository.py CRUD operations (no real DB needed)."""

    def test_db_unavailable_returns_defaults(self):
        from db import repository
        repository.set_db_available(False)
        assert repository.is_db_available() is False

    @pytest.mark.asyncio
    async def test_save_experience_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        result = await repository.save_experience({"id": "test"})
        assert result is None

    @pytest.mark.asyncio
    async def test_load_experiences_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        result = await repository.load_experiences_by_failure("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_count_experiences_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        result = await repository.count_experiences()
        assert result == 0

    @pytest.mark.asyncio
    async def test_upsert_skill_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        await repository.upsert_skill("test:skill", {"name": "test"})
        # Should not raise

    @pytest.mark.asyncio
    async def test_load_skills_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        result = await repository.load_skills_for_agent("sre")
        assert result == []

    @pytest.mark.asyncio
    async def test_save_workflow_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        result = await repository.save_workflow({"workflow_id": "test"})
        assert result is None

    @pytest.mark.asyncio
    async def test_load_workflow_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        result = await repository.load_workflow("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_policy_event_when_unavailable(self):
        from db import repository
        repository.set_db_available(False)
        await repository.save_policy_event("violation", {"action": "test"})
        # Should not raise

    def test_set_and_get_db_available(self):
        from db import repository
        repository.set_db_available(True)
        assert repository.is_db_available() is True
        repository.set_db_available(False)
        assert repository.is_db_available() is False


class TestRedisCache:
    """Test db/redis_cache.py (offline / unavailable mode)."""

    @pytest.mark.asyncio
    async def test_cache_set_noop_when_unavailable(self):
        from db import redis_cache
        redis_cache._available = False
        await redis_cache.cache_set("key", "value")
        # Should not raise

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_when_unavailable(self):
        from db import redis_cache
        redis_cache._available = False
        result = await redis_cache.cache_get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete_noop_when_unavailable(self):
        from db import redis_cache
        redis_cache._available = False
        await redis_cache.cache_delete("key")

    @pytest.mark.asyncio
    async def test_cache_incr_returns_zero_when_unavailable(self):
        from db import redis_cache
        redis_cache._available = False
        result = await redis_cache.cache_incr("counter")
        assert result == 0

    def test_is_available_default_false(self):
        from db import redis_cache
        redis_cache._available = False
        assert redis_cache.is_available() is False


# ─── 2. JWT Authentication Tests ────────────────────────────────────────


class TestJWTAuth:
    """Test real JWT token creation and verification."""

    def test_create_jwt_returns_string(self):
        from middleware.auth import _create_jwt
        token = _create_jwt("test-user", ["viewer"])
        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_jwt_valid_token(self):
        from middleware.auth import _create_jwt, _verify_jwt
        token = _create_jwt("test-user", ["admin", "viewer"])
        claims = _verify_jwt(token)
        assert claims is not None
        assert claims["sub"] == "test-user"
        assert "admin" in claims["roles"]
        assert "viewer" in claims["roles"]
        assert claims["iss"] == "autoforge"

    def test_verify_jwt_expired_token(self):
        from middleware.auth import _create_jwt, _verify_jwt
        token = _create_jwt("expired-user", ["viewer"], expires_delta=timedelta(seconds=-1))
        claims = _verify_jwt(token)
        assert claims is None  # Expired tokens should fail

    def test_verify_jwt_invalid_token(self):
        from middleware.auth import _verify_jwt
        claims = _verify_jwt("garbage.token.here")
        assert claims is None

    def test_verify_jwt_wrong_secret(self):
        from jose import jwt as jose_jwt
        # Create with wrong secret
        payload = {"sub": "hacker", "roles": ["admin"], "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jose_jwt.encode(payload, "wrong-secret", algorithm="HS256")
        from middleware.auth import _verify_jwt
        claims = _verify_jwt(token)
        assert claims is None  # Wrong secret should fail

    def test_token_request_model(self):
        from middleware.auth import TokenRequest
        req = TokenRequest(username="admin", password="admin")
        assert req.username == "admin"
        assert req.password == "admin"

    def test_token_response_model(self):
        from middleware.auth import TokenResponse
        resp = TokenResponse(access_token="abc", expires_in=3600, roles=["viewer"])
        assert resp.token_type == "bearer"
        assert resp.expires_in == 3600


class TestAuthBearerVerification:
    """Test that the auth middleware correctly verifies JWT bearer tokens."""

    @pytest.mark.asyncio
    async def test_bearer_valid_jwt_authenticates(self):
        """A valid JWT should produce an authenticated context with correct roles."""
        from middleware.auth import _create_jwt, _verify_jwt
        token = _create_jwt("dashboard-user", ["admin", "viewer", "operator"])
        claims = _verify_jwt(token)
        assert claims is not None
        assert claims["sub"] == "dashboard-user"
        assert set(claims["roles"]) == {"admin", "viewer", "operator"}

    @pytest.mark.asyncio
    async def test_bearer_invalid_jwt_returns_none(self):
        """An invalid JWT should fail verification."""
        from middleware.auth import _verify_jwt
        assert _verify_jwt("not-a-jwt") is None
        assert _verify_jwt("") is None


# ─── 3. Auth Token Endpoint Tests ───────────────────────────────────────


class TestAuthTokenEndpoint:
    """Test POST /api/v1/auth/token and GET /api/v1/auth/me."""

    @pytest.fixture
    def client(self):
        return _make_test_client()

    def test_token_valid_credentials(self, client):
        resp = client.post("/api/v1/auth/token", json={"username": "admin", "password": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "admin" in data["roles"]
        assert data["expires_in"] > 0

    def test_token_demo_credentials(self, client):
        resp = client.post("/api/v1/auth/token", json={"username": "demo", "password": "demo"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_token_invalid_credentials(self, client):
        resp = client.post("/api/v1/auth/token", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_token_viewer_role(self, client):
        resp = client.post("/api/v1/auth/token", json={"username": "viewer", "password": "viewer"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["roles"] == ["viewer"]

    def test_token_operator_role(self, client):
        resp = client.post("/api/v1/auth/token", json={"username": "operator", "password": "operator"})
        assert resp.status_code == 200
        data = resp.json()
        assert "operator" in data["roles"]
        assert "viewer" in data["roles"]

    def test_auth_me_demo_mode(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True

    def test_auth_me_with_jwt(self, client):
        # First get a token
        token_resp = client.post("/api/v1/auth/token", json={"username": "admin", "password": "admin"})
        token = token_resp.json()["access_token"]
        # Then use it
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["method"] == "bearer"
        assert data["principal"] == "admin"
        assert "admin" in data["roles"]

    def test_auth_me_with_invalid_jwt_fails(self, client):
        """Invalid JWT should now properly reject (not accept any bearer)."""
        # Need to be in production mode to test rejection
        with patch("middleware.auth.settings") as mock_settings:
            mock_settings.DEMO_MODE = False
            mock_settings.APP_ENV = "production"
            mock_settings.JWT_SECRET = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_EXPIRE_MINUTES = 60
            mock_settings.SECRET_KEY = "test-key"
            resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})
            assert resp.status_code == 401


# ─── 4. Celery Worker Dispatch Tests ────────────────────────────────────


class TestCeleryWorkerDispatch:
    """Test webhook → Celery dispatch routing."""

    def test_celery_available_check_function(self):
        """_celery_available should return a boolean without crashing."""
        from api.webhooks import _celery_available
        result = _celery_available()
        assert isinstance(result, bool)

    def test_webhook_dispatches_in_demo_mode(self):
        """In demo mode, webhooks should process in-process, not via Celery."""
        client = _make_test_client()
        resp = client.post("/api/v1/webhooks/test-trigger", json={"scenario": "pipeline_failure_missing_dep"})
        data = resp.json()
        assert data["status"] == "triggered"
        # In demo mode, should NOT have celery_task_id
        assert "celery_task_id" not in data or data.get("dispatch") != "celery"

    def test_worker_module_has_celery_app(self):
        from worker import celery_app
        assert celery_app is not None
        assert celery_app.main == "autoforge"

    def test_worker_has_process_event_task(self):
        from worker import process_event_task
        assert process_event_task.name == "autoforge.process_event"

    def test_worker_has_execute_agent_task(self):
        from worker import execute_agent_task
        assert execute_agent_task.name == "autoforge.execute_agent"

    def test_worker_task_routes(self):
        from worker import celery_app
        routes = celery_app.conf.task_routes
        assert "autoforge.process_event" in routes
        assert routes["autoforge.process_event"]["queue"] == "events"
        assert "autoforge.execute_agent" in routes
        assert routes["autoforge.execute_agent"]["queue"] == "agents"


# ─── 5. Retry History API Tests ─────────────────────────────────────────


class TestRetryHistoryAPI:
    """Test GET /api/v1/dashboard/retries/{workflow_id}."""

    @pytest.fixture
    def client(self):
        return _make_test_client()

    def test_retries_endpoint_returns_200(self, client):
        resp = client.get("/api/v1/dashboard/retries/test-workflow")
        assert resp.status_code == 200

    def test_retries_returns_workflow_id(self, client):
        resp = client.get("/api/v1/dashboard/retries/test-workflow")
        data = resp.json()
        assert data["workflow_id"] == "test-workflow"

    def test_retries_returns_array(self, client):
        resp = client.get("/api/v1/dashboard/retries/test-workflow")
        data = resp.json()
        assert isinstance(data["retries"], list)

    def test_retries_demo_data_shape(self, client):
        resp = client.get("/api/v1/dashboard/retries/demo")
        data = resp.json()
        for retry in data["retries"]:
            assert "attempt" in retry
            assert "maxAttempts" in retry
            assert "agent" in retry
            assert "strategy" in retry
            assert "outcome" in retry
            assert retry["outcome"] in ("success", "failure", "pending")

    def test_retries_demo_has_confidence(self, client):
        resp = client.get("/api/v1/dashboard/retries/demo")
        data = resp.json()
        for retry in data["retries"]:
            assert "confidence" in retry
            assert isinstance(retry["confidence"], (int, float))

    def test_retries_demo_has_duration(self, client):
        resp = client.get("/api/v1/dashboard/retries/demo")
        data = resp.json()
        for retry in data["retries"]:
            assert "duration_ms" in retry


# ─── 6. Agent Communication API Tests ───────────────────────────────────


class TestAgentCommunicationAPI:
    """Test GET /api/v1/dashboard/communication/{workflow_id}."""

    @pytest.fixture
    def client(self):
        return _make_test_client()

    def test_communication_endpoint_returns_200(self, client):
        resp = client.get("/api/v1/dashboard/communication/test-workflow")
        assert resp.status_code == 200

    def test_communication_returns_workflow_id(self, client):
        resp = client.get("/api/v1/dashboard/communication/test-workflow")
        data = resp.json()
        assert data["workflow_id"] == "test-workflow"

    def test_communication_returns_agents_array(self, client):
        resp = client.get("/api/v1/dashboard/communication/demo")
        data = resp.json()
        assert isinstance(data["agents"], list)
        assert len(data["agents"]) > 0

    def test_communication_returns_links_array(self, client):
        resp = client.get("/api/v1/dashboard/communication/demo")
        data = resp.json()
        assert isinstance(data["links"], list)
        assert len(data["links"]) > 0

    def test_communication_link_shape(self, client):
        resp = client.get("/api/v1/dashboard/communication/demo")
        data = resp.json()
        for link in data["links"]:
            assert "from" in link
            assert "to" in link
            assert "dataType" in link
            assert "volume" in link
            assert 0 <= link["volume"] <= 1

    def test_communication_returns_context(self, client):
        resp = client.get("/api/v1/dashboard/communication/demo")
        data = resp.json()
        assert isinstance(data["context"], dict)

    def test_communication_demo_agents_include_core_fleet(self, client):
        resp = client.get("/api/v1/dashboard/communication/demo")
        data = resp.json()
        agents = set(data["agents"])
        assert "sre" in agents
        assert "security" in agents


# ─── 7. Orchestrator Retry History Tests ─────────────────────────────────


class TestOrchestratorRetryHistory:
    """Test that CommandBrain tracks retry history on workflows."""

    def test_get_retry_history_nonexistent_workflow(self):
        from brain.orchestrator import CommandBrain
        brain = CommandBrain()
        result = brain.get_retry_history("nonexistent")
        assert result == []

    def test_get_agent_communication_nonexistent_workflow(self):
        from brain.orchestrator import CommandBrain
        brain = CommandBrain()
        result = brain.get_agent_communication("nonexistent")
        assert result["agents"] == []
        assert result["links"] == []
        assert result["context"] == {}

    def test_get_agent_communication_with_real_workflow(self):
        from brain.orchestrator import CommandBrain
        from models.workflows import Workflow
        brain = CommandBrain()
        wf = Workflow(
            event_type="pipeline_failure",
            project_id="test",
            agents_involved=["sre", "security"],
        )
        wf.publish_context("sre", "root_cause", "missing dep")
        wf.publish_context("sre", "confidence", 0.92)
        brain.state_manager.register_workflow(wf)

        result = brain.get_agent_communication(wf.workflow_id)
        assert "sre" in result["agents"] or "security" in result["agents"]
        assert isinstance(result["context"], dict)
        assert "sre" in result["context"]


# ─── 8. Memory Store Persistence Integration Tests ──────────────────────


class TestMemoryStorePersistence:
    """Test that MemoryStore attempts DB persistence when available."""

    @pytest.mark.asyncio
    async def test_store_experience_calls_db_when_available(self):
        from memory.store import MemoryStore
        from models.agents import AgentExperience

        store = MemoryStore()
        store._db_available = True

        exp = AgentExperience(
            experience_id="test-exp",
            agent_type="sre",
            failure_type="pipeline_failure",
            context_summary="test",
            action_taken="fix",
            outcome="success",
            success=True,
            confidence=0.9,
            fix_time_seconds=1.0,
        )

        # Mock the repository to verify it's called
        with patch("db.repository.save_experience", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = "test-exp"
            await store.store_experience(exp)
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_experience_works_when_db_unavailable(self):
        from memory.store import MemoryStore
        from models.agents import AgentExperience

        store = MemoryStore()
        store._db_available = False

        exp = AgentExperience(
            experience_id="test-exp-2",
            agent_type="sre",
            failure_type="pipeline_failure",
            context_summary="test",
            action_taken="fix",
            outcome="success",
            success=True,
            confidence=0.9,
            fix_time_seconds=1.0,
        )

        await store.store_experience(exp)
        assert len(store._experiences) == 1

    @pytest.mark.asyncio
    async def test_recall_tries_db_on_empty_memory(self):
        from memory.store import MemoryStore

        store = MemoryStore()
        store._db_available = True

        with patch("db.repository.load_experiences_by_failure", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = [{"agent": "sre", "action": "fix", "success": True, "confidence": 0.9}]
            result = await store.recall("sre", {"event_type": "pipeline_failure"})
            mock_load.assert_called_once_with("pipeline_failure", limit=50)
            assert "similar_fixes" in result

    @pytest.mark.asyncio
    async def test_policy_violation_persists(self):
        from memory.store import MemoryStore

        store = MemoryStore()
        store._db_available = True

        with patch("db.repository.save_policy_event", new_callable=AsyncMock) as mock_save:
            await store.record_policy_violation("dangerous_action", "too risky", "sre")
            mock_save.assert_called_once_with("violation", {
                "action": "dangerous_action",
                "reason": "too risky",
                "agent_type": "sre",
            })

    @pytest.mark.asyncio
    async def test_policy_override_persists(self):
        from memory.store import MemoryStore

        store = MemoryStore()
        store._db_available = True

        with patch("db.repository.save_policy_event", new_callable=AsyncMock) as mock_save:
            await store.record_policy_override("dangerous_action", "admin-user")
            mock_save.assert_called_once_with("override", {
                "action": "dangerous_action",
                "approved_by": "admin-user",
            })


# ─── 9. Memory Store Initialization Tests ───────────────────────────────


class TestMemoryStoreInit:
    """Test MemoryStore initialization with/without DB."""

    @pytest.mark.asyncio
    async def test_init_demo_mode_skips_db(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        with patch("config.settings") as mock_settings:
            mock_settings.DEMO_MODE = True
            await store.initialize()
            assert store._db_available is False
            assert store._redis_available is False

    @pytest.mark.asyncio
    async def test_shutdown_no_crash(self):
        from memory.store import MemoryStore
        store = MemoryStore()
        store._db_available = False
        store._redis_available = False
        await store.shutdown()


# ─── 10. End-to-End API Integration ─────────────────────────────────────


class TestFullAPIIntegration:
    """Full API round-trip tests for new endpoints."""

    @pytest.fixture
    def client(self):
        return _make_test_client()

    def test_full_auth_flow(self, client):
        """Login → get token → use token → inspect me."""
        # Login
        resp = client.post("/api/v1/auth/token", json={"username": "admin", "password": "admin"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # Use token to access /me
        me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["principal"] == "admin"
        assert "admin" in me_data["roles"]

    def test_retries_and_communication_both_work(self, client):
        """Both new dashboard endpoints should work together."""
        retries_resp = client.get("/api/v1/dashboard/retries/demo")
        comm_resp = client.get("/api/v1/dashboard/communication/demo")
        assert retries_resp.status_code == 200
        assert comm_resp.status_code == 200

    def test_existing_endpoints_still_work(self, client):
        """Verify no regressions on existing endpoints."""
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/dashboard/overview").status_code == 200
        assert client.get("/api/v1/dashboard/activity").status_code == 200
        assert client.get("/api/v1/dashboard/learning").status_code == 200
        assert client.get("/api/v1/dashboard/carbon").status_code == 200

    def test_webhook_test_trigger_still_works(self, client):
        resp = client.post("/api/v1/webhooks/test-trigger", json={"scenario": "pipeline_failure_missing_dep"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "triggered"
