"""
AutoForge — Backend Test Suite
"""
import pytest
import asyncio


class TestConfig:
    def test_config_loads(self):
        from backend.config import settings
        assert settings is not None

    def test_config_has_key_fields(self):
        from backend.config import settings
        assert hasattr(settings, "LOG_LEVEL")
        assert hasattr(settings, "APP_PORT")
        assert hasattr(settings, "ANTHROPIC_MODEL")
        assert hasattr(settings, "GREENOPS_CARBON_FACTOR")


class TestModels:
    def test_event_type_enum(self):
        from backend.models.events import EventType
        assert EventType.PIPELINE_FAILURE.value == "pipeline_failure"
        assert EventType.MERGE_REQUEST_OPENED.value == "merge_request_opened"
        assert EventType.SECURITY_ALERT.value == "security_alert"
        assert EventType.PUSH.value == "push"

    def test_normalized_event_creation(self):
        from backend.models.events import NormalizedEvent, EventType
        event = NormalizedEvent(
            event_type=EventType.PIPELINE_FAILURE,
            project_id="proj-1",
            project_name="test-project",
            ref="main",
            source="test",
            payload={"test": True},
        )
        assert event.event_type == EventType.PIPELINE_FAILURE
        assert event.project_id == "proj-1"

    def test_workflow_model(self):
        from backend.models.workflows import Workflow, WorkflowStatus
        wf = Workflow(
            event_type="pipeline_failure",
            project_id="proj-1",
            project_name="test-project",
            ref="main",
        )
        assert wf.status == WorkflowStatus.PENDING
        assert wf.workflow_id is not None
        assert len(wf.tasks) == 0

    def test_workflow_to_dict(self):
        from backend.models.workflows import Workflow
        wf = Workflow(
            event_type="test_event",
            project_id="proj-1",
            project_name="test",
            ref="main",
        )
        d = wf.to_dict()
        assert d["event_type"] == "test_event"
        assert "status" in d
        assert "created_at" in d

    def test_agent_type_enum(self):
        from backend.models.agents import AgentType
        assert AgentType.SRE.value == "sre"
        assert AgentType.SECURITY.value == "security"
        assert AgentType.QA.value == "qa"
        assert AgentType.REVIEW.value == "review"
        assert AgentType.DOCS.value == "docs"
        assert AgentType.GREENOPS.value == "greenops"

    def test_agent_task_model(self):
        from backend.models.workflows import AgentTask
        task = AgentTask(
            workflow_id="wf-test-1",
            agent_type="sre",
            action="diagnose_failure",
            input_data={"error": "test"},
        )
        assert task.agent_type == "sre"
        assert task.action == "diagnose_failure"
        assert task.task_id is not None

    def test_agent_experience_model(self):
        from backend.models.agents import AgentExperience
        exp = AgentExperience(
            experience_id="exp-1",
            agent_type="sre",
            failure_type="pipeline_failure",
            context_summary="Missing dependency numpy",
            action_taken="Added numpy to requirements.txt",
            outcome="Pipeline passed after fix",
            success=True,
            confidence=0.85,
            fix_time_seconds=45.0,
        )
        assert exp.agent_type == "sre"
        assert exp.success is True


class TestBrainRouter:
    def test_route_pipeline_failure(self):
        from backend.brain.router import AgentRouter
        router = AgentRouter()
        agents = router.get_agents_for_event("pipeline_failure")
        assert "sre" in agents

    def test_route_security_alert(self):
        from backend.brain.router import AgentRouter
        router = AgentRouter()
        agents = router.get_agents_for_event("security_alert")
        assert "security" in agents

    def test_route_mr_opened(self):
        from backend.brain.router import AgentRouter
        router = AgentRouter()
        agents = router.get_agents_for_event("merge_request_opened")
        assert "review" in agents

    def test_get_action_for_agent(self):
        from backend.brain.router import AgentRouter
        router = AgentRouter()
        action = router.get_action_for_agent("pipeline_failure", "sre")
        assert isinstance(action, str)
        assert len(action) > 0


class TestMemoryStore:
    def test_memory_store_creation(self):
        from backend.memory.store import MemoryStore
        store = MemoryStore()
        assert store is not None

    @pytest.mark.asyncio
    async def test_store_experience(self):
        from backend.memory.store import MemoryStore
        from backend.models.agents import AgentExperience
        store = MemoryStore()
        exp = AgentExperience(
            experience_id="exp-test-1",
            agent_type="sre",
            failure_type="pipeline_failure",
            context_summary="Missing numpy",
            action_taken="Added to requirements",
            outcome="Fixed",
            success=True,
            confidence=0.85,
            fix_time_seconds=45.0,
        )
        await store.store_experience(exp)

    @pytest.mark.asyncio
    async def test_recall(self):
        from backend.memory.store import MemoryStore
        from backend.models.agents import AgentExperience
        store = MemoryStore()
        exp = AgentExperience(
            experience_id="exp-test-2",
            agent_type="sre",
            failure_type="pipeline_failure",
            context_summary="Missing numpy",
            action_taken="Added to requirements",
            outcome="Fixed",
            success=True,
            confidence=0.9,
            fix_time_seconds=30.0,
        )
        await store.store_experience(exp)
        memories = await store.recall("sre", {"event_type": "pipeline_failure"})
        assert isinstance(memories, dict)


class TestTelemetry:
    def test_collector_creation(self):
        from backend.telemetry.collector import TelemetryCollector
        collector = TelemetryCollector()
        assert collector is not None

    @pytest.mark.asyncio
    async def test_log_event(self):
        from backend.telemetry.collector import TelemetryCollector
        collector = TelemetryCollector()
        await collector.log_event(
            event_type="pipeline_failure",
            data={"project": "test", "success": True},
        )

    @pytest.mark.asyncio
    async def test_get_current_metrics(self):
        from backend.telemetry.collector import TelemetryCollector
        collector = TelemetryCollector()
        metrics = await collector.get_current_metrics()
        assert isinstance(metrics, dict)

    @pytest.mark.asyncio
    async def test_meta_intelligence_score(self):
        from backend.telemetry.collector import TelemetryCollector
        collector = TelemetryCollector()
        score = await collector.calculate_meta_intelligence()
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100


class TestConflictResolver:
    def test_no_conflicts_single_task(self):
        from backend.brain.conflict_resolver import ConflictResolver
        from backend.models.workflows import AgentTask
        resolver = ConflictResolver()
        tasks = [
            AgentTask(
                workflow_id="wf-test-1",
                agent_type="sre",
                action="diagnose_failure",
                input_data={},
            )
        ]
        resolved = resolver.resolve(tasks)
        assert len(resolved) == 1


class TestPolicyEngine:
    def test_check_simple_task(self):
        from backend.brain.policy_engine import PolicyEngine
        from backend.models.workflows import AgentTask, Workflow
        engine = PolicyEngine()
        task = AgentTask(
            workflow_id="wf-test-1",
            agent_type="sre",
            action="diagnose_failure",
            input_data={},
        )
        workflow = Workflow(
            event_type="pipeline_failure",
            project_id="proj-1",
            project_name="test",
            ref="main",
        )
        allowed, reason = engine.check_policy(task, workflow)
        assert allowed is True


class TestStateManager:
    def test_register_and_get_workflow(self):
        from backend.brain.state_manager import StateManager
        from backend.models.workflows import Workflow
        manager = StateManager()
        wf = Workflow(
            event_type="pipeline_failure",
            project_id="proj-1",
            project_name="test",
            ref="main",
        )
        manager.register_workflow(wf)
        retrieved = manager.get_workflow(wf.workflow_id)
        assert retrieved is not None
        assert retrieved.workflow_id == wf.workflow_id

    def test_get_system_stats(self):
        from backend.brain.state_manager import StateManager
        manager = StateManager()
        stats = manager.get_system_stats()
        assert "total_workflows" in stats
        assert "active_workflows" in stats

    def test_get_workflows(self):
        from backend.brain.state_manager import StateManager
        from backend.models.workflows import Workflow
        manager = StateManager()
        wf = Workflow(
            event_type="pipeline_failure",
            project_id="proj-1",
            project_name="test",
            ref="main",
        )
        manager.register_workflow(wf)
        workflows = manager.get_workflows()
        assert len(workflows) >= 1
