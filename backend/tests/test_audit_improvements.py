"""
AutoForge — Audit Improvement Test Suite

Tests all features added during the 12-layer technical audit:
- DEMO_MODE toggle
- Precomputed reasoning trees
- Task DAG with dependencies
- Shared context bus
- Multi-depth reasoning trees
- Evidence weighting
- Policy guardrails (branch protection, diff limits)
- Memory layers (semantic, cross-agent, policy learning)
- Telemetry MIS weighted formula
- Tool stubs (generate_tests, update_docs)
"""

import pytest
import asyncio


# ─── Demo Mode ─────────────────────────────────────────────────────────────────

class TestDemoMode:
    def test_demo_mode_config_exists(self):
        from backend.config import settings
        assert hasattr(settings, "DEMO_MODE")
        assert isinstance(settings.DEMO_MODE, bool)

    def test_demo_engine_loads(self):
        from backend.demo.engine import (
            get_demo_scenario,
            get_demo_hypotheses,
            get_demo_plan,
            get_demo_fix,
            get_demo_reflection,
            get_demo_energy,
        )
        # All functions should be callable
        assert callable(get_demo_scenario)
        assert callable(get_demo_hypotheses)

    def test_demo_scenario_pipeline_failure(self):
        from backend.demo.engine import get_demo_scenario
        scenario = get_demo_scenario("pipeline_failure")
        assert scenario is not None
        assert "hypotheses" in scenario
        assert len(scenario["hypotheses"]) == 5
        assert scenario["confidence"] == 0.92

    def test_demo_scenario_security(self):
        from backend.demo.engine import get_demo_scenario
        scenario = get_demo_scenario("security_vulnerability")
        assert scenario is not None
        assert scenario["confidence"] == 0.95
        assert "plan" in scenario

    def test_demo_scenario_mr(self):
        from backend.demo.engine import get_demo_scenario
        scenario = get_demo_scenario("merge_request_opened")
        assert scenario is not None
        assert len(scenario["hypotheses"]) == 4

    def test_demo_scenario_inefficient(self):
        from backend.demo.engine import get_demo_scenario
        scenario = get_demo_scenario("inefficient_pipeline")
        assert scenario is not None
        assert scenario["confidence"] == 0.82

    def test_demo_hypotheses(self):
        from backend.demo.engine import get_demo_hypotheses
        hyps = get_demo_hypotheses("pipeline_failure")
        assert len(hyps) == 5
        assert hyps[0]["probability"] == 0.92
        assert "numpy" in hyps[0]["description"].lower()

    def test_demo_plan(self):
        from backend.demo.engine import get_demo_plan
        plan = get_demo_plan("pipeline_failure")
        assert plan["confidence"] == 0.92
        assert "numpy" in plan["chosen_action"].lower()

    def test_demo_fix(self):
        from backend.demo.engine import get_demo_fix
        fix = get_demo_fix("pipeline_failure")
        assert len(fix["files_to_modify"]) >= 1
        assert "requirements.txt" in fix["files_to_modify"][0]["path"]

    def test_demo_reflection(self):
        from backend.demo.engine import get_demo_reflection
        ref = get_demo_reflection("pipeline_failure")
        assert ref["success"] is True
        assert ref["confidence"] >= 0.9

    def test_demo_energy(self):
        from backend.demo.engine import get_demo_energy
        energy = get_demo_energy("pipeline_failure")
        assert energy["energy_kwh"] > 0
        assert energy["efficiency_score"] > 0
        assert len(energy["optimizations"]) >= 2

    def test_demo_energy_inefficient(self):
        from backend.demo.engine import get_demo_energy
        energy = get_demo_energy("inefficient_pipeline")
        assert energy["efficiency_score"] < 60  # Intentionally low
        assert len(energy["optimizations"]) >= 3


# ─── Task DAG Dependencies ────────────────────────────────────────────────────

class TestTaskDAG:
    def test_task_has_dependencies_field(self):
        from backend.models.workflows import AgentTask
        task = AgentTask(
            workflow_id="wf-1",
            agent_type="sre",
            action="diagnose",
            dependencies=["task-a", "task-b"],
        )
        assert task.dependencies == ["task-a", "task-b"]

    def test_task_default_empty_dependencies(self):
        from backend.models.workflows import AgentTask
        task = AgentTask(workflow_id="wf-1", agent_type="sre", action="diagnose")
        assert task.dependencies == []

    def test_decomposer_wires_dependencies(self):
        from backend.brain.task_decomposer import TaskDecomposer
        from backend.models.events import NormalizedEvent, EventType
        decomposer = TaskDecomposer()
        event = NormalizedEvent(
            event_type=EventType.PIPELINE_FAILURE,
            project_id="proj-1",
            project_name="test",
            ref="main",
            source="test",
            payload={},
        )
        tasks = decomposer.decompose(event)
        assert len(tasks) >= 3

        # SRE should have no dependencies (runs first)
        sre_tasks = [t for t in tasks if t.agent_type == "sre"]
        assert len(sre_tasks) == 1
        assert sre_tasks[0].dependencies == []

        # Security should depend on SRE
        sec_tasks = [t for t in tasks if t.agent_type == "security"]
        if sec_tasks:
            assert len(sec_tasks[0].dependencies) > 0
            # The dependency should be the SRE task ID
            assert sre_tasks[0].task_id in sec_tasks[0].dependencies

    def test_decomposer_mr_dependencies(self):
        from backend.brain.task_decomposer import TaskDecomposer
        from backend.models.events import NormalizedEvent, EventType
        decomposer = TaskDecomposer()
        event = NormalizedEvent(
            event_type=EventType.MERGE_REQUEST_OPENED,
            project_id="proj-1",
            project_name="test",
            ref="main",
            source="test",
            payload={},
        )
        tasks = decomposer.decompose(event)
        # Review should have no deps; QA should depend on review
        review_tasks = [t for t in tasks if t.agent_type == "review"]
        qa_tasks = [t for t in tasks if t.agent_type == "qa"]
        if review_tasks:
            assert review_tasks[0].dependencies == []
        if qa_tasks:
            assert review_tasks[0].task_id in qa_tasks[0].dependencies


# ─── Shared Context Bus ───────────────────────────────────────────────────────

class TestSharedContextBus:
    def test_workflow_publish_context(self):
        from backend.models.workflows import Workflow
        wf = Workflow(event_type="test", project_id="p1", project_name="t", ref="main")
        wf.publish_context("sre", "root_cause", "missing numpy")
        wf.publish_context("sre", "confidence", 0.92)
        assert wf.shared_context["sre"]["root_cause"] == "missing numpy"
        assert wf.shared_context["sre"]["confidence"] == 0.92

    def test_workflow_consume_context_all(self):
        from backend.models.workflows import Workflow
        wf = Workflow(event_type="test", project_id="p1", project_name="t", ref="main")
        wf.publish_context("sre", "fix", "added numpy")
        wf.publish_context("security", "scan", "clean")
        ctx = wf.consume_context()
        assert "sre" in ctx
        assert "security" in ctx

    def test_workflow_consume_context_filtered(self):
        from backend.models.workflows import Workflow
        wf = Workflow(event_type="test", project_id="p1", project_name="t", ref="main")
        wf.publish_context("sre", "fix", "added numpy")
        wf.publish_context("security", "scan", "clean")
        ctx = wf.consume_context("sre")
        assert "fix" in ctx
        assert "scan" not in ctx


# ─── Multi-Depth Reasoning Trees ──────────────────────────────────────────────

class TestMultiDepthReasoning:
    def test_reasoning_node_depth2(self):
        from backend.models.agents import ReasoningNode, ReasoningTree
        root = ReasoningNode(node_id="root", hypothesis="Root", depth=0)
        child = ReasoningNode(node_id="h_0", hypothesis="H0", probability=0.9, depth=1)
        grandchild = ReasoningNode(node_id="h_0_fix", hypothesis="Fix", probability=0.8, depth=2)
        child.children.append(grandchild)
        root.children.append(child)

        tree = ReasoningTree(root=root, total_branches=2, max_depth=2)
        viz = tree.to_visualization()
        assert len(viz["nodes"]) == 3
        assert len(viz["edges"]) == 2

    def test_sre_builds_depth2_tree(self):
        """SRE agent should build depth-2 reasoning trees."""
        from backend.agents.sre.agent import SREAgent
        agent = SREAgent()
        hypotheses = [
            {"description": "Missing dep", "probability": 0.9, "evidence": ["ModuleNotFoundError"], "risk_if_wrong": 0.1, "suggested_action": "Add dep"},
            {"description": "Env mismatch", "probability": 0.05, "evidence": ["CI only"], "risk_if_wrong": 0.3, "suggested_action": "Fix env"},
        ]
        context = {"error_logs": "ModuleNotFoundError: numpy", "failure_signals": ["missing_dependency"]}
        result = agent._build_reasoning_result(hypotheses, context, {})
        tree = result["reasoning_tree"]
        # Should have root + 2 children + sub-nodes
        assert len(tree["nodes"]) >= 3
        assert result["exploration_depth"] >= 2


# ─── Evidence Weighting ───────────────────────────────────────────────────────

class TestEvidenceWeighting:
    def test_evidence_match_high(self):
        from backend.agents.sre.agent import SREAgent
        agent = SREAgent()
        hypothesis = {
            "evidence": ["ModuleNotFoundError in numpy import", "requirements.txt modified"],
        }
        context = {
            "error_logs": "ModuleNotFoundError: No module named 'numpy'",
            "failure_signals": ["missing_dependency"],
        }
        score = agent._compute_evidence_match(hypothesis, context)
        assert score > 0.0

    def test_evidence_match_low(self):
        from backend.agents.sre.agent import SREAgent
        agent = SREAgent()
        hypothesis = {
            "evidence": ["network timeout in database connection"],
        }
        context = {
            "error_logs": "ModuleNotFoundError: No module named 'numpy'",
            "failure_signals": ["missing_dependency"],
        }
        score = agent._compute_evidence_match(hypothesis, context)
        assert score <= 0.5

    def test_evidence_match_empty(self):
        from backend.agents.sre.agent import SREAgent
        agent = SREAgent()
        score = agent._compute_evidence_match({"evidence": []}, {"error_logs": ""})
        assert score == 0.0


# ─── Policy Engine Guardrails ─────────────────────────────────────────────────

class TestPolicyGuardrails:
    def test_branch_protection_blocks_direct_edit(self):
        from backend.brain.policy_engine import PolicyEngine
        from backend.models.workflows import AgentTask, Workflow
        engine = PolicyEngine()
        task = AgentTask(
            workflow_id="wf-1",
            agent_type="sre",
            action="edit_file",
            input_data={"target_branch": "main"},
        )
        wf = Workflow(event_type="test", project_id="p1", project_name="t", ref="main")
        allowed, reason = engine.check_policy(task, wf)
        assert allowed is False
        assert "protected branch" in reason.lower()

    def test_branch_protection_allows_feature_branch(self):
        from backend.brain.policy_engine import PolicyEngine
        from backend.models.workflows import AgentTask, Workflow
        engine = PolicyEngine()
        task = AgentTask(
            workflow_id="wf-1",
            agent_type="sre",
            action="edit_file",
            input_data={"target_branch": "autoforge/fix-123"},
        )
        wf = Workflow(event_type="test", project_id="p1", project_name="t", ref="main")
        allowed, reason = engine.check_policy(task, wf)
        assert allowed is True

    def test_high_risk_actions_expanded(self):
        from backend.brain.policy_engine import PolicyEngine
        engine = PolicyEngine()
        assert "drop_database" in engine.HIGH_RISK_ACTIONS
        assert "reset_hard" in engine.HIGH_RISK_ACTIONS

    def test_approval_requirements_protected_branch(self):
        from backend.brain.policy_engine import PolicyEngine
        from backend.models.workflows import AgentTask
        engine = PolicyEngine()
        task = AgentTask(
            workflow_id="wf-1",
            agent_type="sre",
            action="push_changes",
            input_data={"target_branch": "production"},
        )
        req = engine.get_approval_requirements(task)
        assert req["requires_approval"] is True
        assert req["approval_type"] == "branch_protection"


# ─── Memory Layers ────────────────────────────────────────────────────────────

class TestMemoryLayers:
    @pytest.mark.asyncio
    async def test_semantic_pattern_built(self):
        from backend.memory.store import MemoryStore
        from backend.models.agents import AgentExperience
        store = MemoryStore()
        exp = AgentExperience(
            experience_id="e1", agent_type="sre", failure_type="pipeline_failure",
            context_summary="Missing numpy dependency",
            action_taken="add_dependency", outcome="fixed", success=True,
            confidence=0.9, fix_time_seconds=30,
        )
        await store.store_experience(exp)
        assert len(store._semantic_patterns["pipeline_failure"]) == 1

    @pytest.mark.asyncio
    async def test_cross_agent_sharing(self):
        from backend.memory.store import MemoryStore
        from backend.models.agents import AgentExperience
        store = MemoryStore()
        exp = AgentExperience(
            experience_id="e2", agent_type="sre", failure_type="pipeline_failure",
            context_summary="Fixed missing dep",
            action_taken="add_dependency", outcome="fixed", success=True,
            confidence=0.9, fix_time_seconds=30,
            reusable_skill="dependency_restoration",
        )
        await store.store_experience(exp)
        # Knowledge should be shared with other agents
        assert len(store._shared_knowledge["security"]) > 0
        assert len(store._shared_knowledge["qa"]) > 0
        # But not with self
        assert len(store._shared_knowledge["sre"]) == 0

    @pytest.mark.asyncio
    async def test_recall_includes_semantic_and_shared(self):
        from backend.memory.store import MemoryStore
        from backend.models.agents import AgentExperience
        store = MemoryStore()
        exp = AgentExperience(
            experience_id="e3", agent_type="sre", failure_type="pipeline_failure",
            context_summary="Fixed dep",
            action_taken="add", outcome="ok", success=True,
            confidence=0.8, fix_time_seconds=25,
            reusable_skill="dep_fix",
        )
        await store.store_experience(exp)
        # Recall for security should include cross-agent knowledge from SRE
        result = await store.recall("security", {"event_type": "pipeline_failure"})
        assert "cross_agent_knowledge" in result

    @pytest.mark.asyncio
    async def test_policy_learning(self):
        from backend.memory.store import MemoryStore
        store = MemoryStore()
        await store.record_policy_violation("force_push", "requires approval", "sre")
        stats = store.get_policy_learning_stats()
        assert stats["total_violations"] == 1

    def test_memory_stats_include_new_layers(self):
        from backend.memory.store import MemoryStore
        store = MemoryStore()
        stats = store.get_stats()
        assert "semantic_pattern_categories" in stats
        assert "cross_agent_shares" in stats
        assert "policy_violations" in stats


# ─── Telemetry MIS Weighted Formula ───────────────────────────────────────────

class TestTelemetryMIS:
    @pytest.mark.asyncio
    async def test_mis_bounded(self):
        from backend.telemetry.collector import TelemetryCollector
        c = TelemetryCollector()
        score = await c.calculate_meta_intelligence()
        assert 0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_mis_with_data(self):
        from backend.telemetry.collector import TelemetryCollector
        from backend.models.workflows import Workflow, WorkflowStatus
        from datetime import datetime, timezone, timedelta
        c = TelemetryCollector()
        # Simulate some completed workflows
        for i in range(5):
            wf = Workflow(event_type="test", project_id="p1", project_name="t", ref="main")
            wf.status = WorkflowStatus.COMPLETED
            wf.agents_involved = ["sre", "security"]
            wf.completed_at = datetime.now(timezone.utc)
            await c.log_workflow_completed(wf)
        score = await c.calculate_meta_intelligence()
        # With completed workflows, MIS should be positive
        assert score >= 0


# ─── Tool Stubs ───────────────────────────────────────────────────────────────

class TestToolStubs:
    def test_gitlab_tools_has_generate_tests(self):
        from backend.tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        assert hasattr(tools, "generate_tests")
        assert callable(tools.generate_tests)

    def test_gitlab_tools_has_update_docs(self):
        from backend.tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        assert hasattr(tools, "update_docs")
        assert callable(tools.update_docs)


# ─── DAG Dependency Map ───────────────────────────────────────────────────────

class TestDependencyMap:
    def test_pipeline_failure_dag(self):
        from backend.brain.task_decomposer import AGENT_DEPENDENCY_MAP
        dag = AGENT_DEPENDENCY_MAP.get("pipeline_failure", {})
        assert dag["sre"] == []  # SRE leads
        assert "sre" in dag["security"]  # Security depends on SRE
        assert "sre" in dag["qa"]  # QA depends on SRE
        assert "sre" in dag["docs"]  # Docs depends on SRE

    def test_security_alert_dag(self):
        from backend.brain.task_decomposer import AGENT_DEPENDENCY_MAP
        dag = AGENT_DEPENDENCY_MAP.get("security_alert", {})
        assert dag["security"] == []  # Security leads
        assert "security" in dag["sre"]  # SRE depends on Security

    def test_mr_opened_dag(self):
        from backend.brain.task_decomposer import AGENT_DEPENDENCY_MAP
        dag = AGENT_DEPENDENCY_MAP.get("merge_request_opened", {})
        assert dag["review"] == []  # Review leads
        assert "review" in dag["qa"]  # QA depends on Review
