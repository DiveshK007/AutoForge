"""
AutoForge — Dashboard & Telemetry Demo-State API Tests

Verifies that all dashboard and telemetry endpoints return
the correct shapes and rich demo data when in DEMO_MODE with
no real workflows.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Dashboard /overview
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardOverview:
    def test_returns_200(self, client):
        r = client.get("/api/v1/dashboard/overview")
        assert r.status_code == 200

    def test_overview_has_required_fields(self, client):
        data = client.get("/api/v1/dashboard/overview").json()
        required = {"system_status", "total_workflows", "active_workflows",
                     "success_rate", "agents", "metrics", "meta_intelligence_score"}
        assert required.issubset(set(data.keys())), f"Missing fields: {required - set(data.keys())}"

    def test_overview_agents_shape(self, client):
        agents = client.get("/api/v1/dashboard/overview").json()["agents"]
        assert isinstance(agents, list)
        assert len(agents) >= 6
        first = agents[0]
        for key in ("name", "type", "status", "tasks_completed", "success_rate", "avg_confidence"):
            assert key in first, f"Agent missing field: {key}"

    def test_overview_metrics_shape(self, client):
        metrics = client.get("/api/v1/dashboard/overview").json()["metrics"]
        assert isinstance(metrics, dict)
        for key in ("success_rate", "avg_fix_time", "avg_confidence", "total_events",
                     "avg_reasoning_depth", "collaboration_index", "self_correction_rate",
                     "carbon_saved_grams"):
            assert key in metrics, f"Metrics missing field: {key}"

    def test_overview_meta_intelligence_score(self, client):
        score = client.get("/api/v1/dashboard/overview").json()["meta_intelligence_score"]
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100


# ═══════════════════════════════════════════════════════════════════════════════
#  Dashboard /agents
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardAgents:
    def test_returns_200(self, client):
        r = client.get("/api/v1/dashboard/agents")
        assert r.status_code == 200

    def test_agents_response_shape(self, client):
        data = client.get("/api/v1/dashboard/agents").json()
        assert "agents" in data
        assert "count" in data
        assert data["count"] == len(data["agents"])

    def test_agents_have_required_fields(self, client):
        agents = client.get("/api/v1/dashboard/agents").json()["agents"]
        for a in agents:
            for key in ("name", "type", "status", "tasks_completed", "success_rate", "avg_confidence"):
                assert key in a, f"Agent {a.get('name', '?')} missing field: {key}"

    def test_agents_types_cover_fleet(self, client):
        agents = client.get("/api/v1/dashboard/agents").json()["agents"]
        types = {a["type"] for a in agents}
        assert len(types) >= 5  # sre, security, qa, review, docs, greenops


# ═══════════════════════════════════════════════════════════════════════════════
#  Dashboard /activity and /activity-feed
# ═══════════════════════════════════════════════════════════════════════════════

class TestActivityFeed:
    def test_activity_returns_200(self, client):
        r = client.get("/api/v1/dashboard/activity")
        assert r.status_code == 200

    def test_activity_feed_returns_200(self, client):
        r = client.get("/api/v1/dashboard/activity-feed")
        assert r.status_code == 200

    def test_activity_is_flat_array(self, client):
        data = client.get("/api/v1/dashboard/activity").json()
        assert isinstance(data, list), "Activity must be a flat array"

    def test_activity_has_items(self, client):
        data = client.get("/api/v1/dashboard/activity").json()
        assert len(data) >= 5

    def test_activity_item_shape(self, client):
        items = client.get("/api/v1/dashboard/activity").json()
        first = items[0]
        for key in ("timestamp", "type", "description", "status"):
            assert key in first, f"Activity item missing field: {key}"

    def test_activity_limit_param(self, client):
        data = client.get("/api/v1/dashboard/activity?limit=3").json()
        assert len(data) <= 3

    def test_activity_and_feed_return_same(self, client):
        a = client.get("/api/v1/dashboard/activity").json()
        b = client.get("/api/v1/dashboard/activity-feed").json()
        assert a == b


# ═══════════════════════════════════════════════════════════════════════════════
#  Dashboard /reasoning/{workflow_id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestReasoningVisualization:
    # These are the actual DEMO_REASONING_TREES keys
    DEMO_SCENARIOS = [
        "pipeline_failure",
        "security_vulnerability",
        "merge_request_opened",
        "inefficient_pipeline",
    ]
    # Frontend sends these aliased names
    FRONTEND_ALIASES = [
        "pipeline_failure_missing_dep",
    ]

    def test_reasoning_known_scenario_returns_200(self, client):
        for sc in self.DEMO_SCENARIOS:
            r = client.get(f"/api/v1/dashboard/reasoning/{sc}")
            assert r.status_code == 200, f"Scenario {sc} failed: {r.status_code}"

    def test_reasoning_alias_returns_200(self, client):
        for alias in self.FRONTEND_ALIASES:
            r = client.get(f"/api/v1/dashboard/reasoning/{alias}")
            assert r.status_code == 200, f"Alias {alias} failed: {r.status_code}"

    def test_reasoning_has_nodes_and_edges(self, client):
        for sc in self.DEMO_SCENARIOS:
            data = client.get(f"/api/v1/dashboard/reasoning/{sc}").json()
            assert "nodes" in data and "edges" in data
            assert len(data["nodes"]) >= 5, f"{sc}: expected ≥5 nodes, got {len(data['nodes'])}"
            assert len(data["edges"]) >= 4, f"{sc}: expected ≥4 edges, got {len(data['edges'])}"

    def test_reasoning_node_shape(self, client):
        data = client.get(f"/api/v1/dashboard/reasoning/{self.DEMO_SCENARIOS[0]}").json()
        node = data["nodes"][0]
        for key in ("id", "label", "type", "confidence"):
            assert key in node, f"Reasoning node missing: {key}"

    def test_reasoning_edge_shape(self, client):
        data = client.get(f"/api/v1/dashboard/reasoning/{self.DEMO_SCENARIOS[0]}").json()
        edge = data["edges"][0]
        for key in ("source", "target", "label"):
            assert key in edge, f"Reasoning edge missing: {key}"

    def test_reasoning_node_types_span_full_chain(self, client):
        data = client.get(f"/api/v1/dashboard/reasoning/{self.DEMO_SCENARIOS[0]}").json()
        types = {n["type"] for n in data["nodes"]}
        expected = {"event", "perception", "hypothesis", "reasoning", "plan", "action", "reflection", "result"}
        assert expected.issubset(types), f"Missing node types: {expected - types}"

    def test_reasoning_unknown_scenario_returns_404(self, client):
        r = client.get("/api/v1/dashboard/reasoning/nonexistent-wf-id")
        assert r.status_code == 404

    def test_reasoning_contains_workflow_id(self, client):
        sc = self.DEMO_SCENARIOS[1]
        data = client.get(f"/api/v1/dashboard/reasoning/{sc}").json()
        assert data["workflow_id"] == sc


# ═══════════════════════════════════════════════════════════════════════════════
#  Dashboard /learning
# ═══════════════════════════════════════════════════════════════════════════════

class TestLearningDashboard:
    def test_returns_200(self, client):
        r = client.get("/api/v1/dashboard/learning")
        assert r.status_code == 200

    def test_learning_shape(self, client):
        data = client.get("/api/v1/dashboard/learning").json()
        for key in ("learning_curve", "memory_utilization", "knowledge_reuse_count",
                     "reasoning_depth_avg", "meta_intelligence_score"):
            assert key in data, f"Learning missing: {key}"

    def test_learning_curve_is_array(self, client):
        curve = client.get("/api/v1/dashboard/learning").json()["learning_curve"]
        assert isinstance(curve, list)
        assert len(curve) >= 10

    def test_learning_curve_item_shape(self, client):
        item = client.get("/api/v1/dashboard/learning").json()["learning_curve"][0]
        for key in ("event_number", "success", "confidence", "fix_time", "cumulative_success_rate"):
            assert key in item, f"Learning curve item missing: {key}"

    def test_learning_curve_is_ordered(self, client):
        curve = client.get("/api/v1/dashboard/learning").json()["learning_curve"]
        nums = [p["event_number"] for p in curve]
        assert nums == sorted(nums), "Learning curve should be ordered by event_number"

    def test_meta_intelligence_score_range(self, client):
        score = client.get("/api/v1/dashboard/learning").json()["meta_intelligence_score"]
        assert 0 <= score <= 100


# ═══════════════════════════════════════════════════════════════════════════════
#  Dashboard /carbon
# ═══════════════════════════════════════════════════════════════════════════════

class TestCarbonDashboard:
    def test_returns_200(self, client):
        r = client.get("/api/v1/dashboard/carbon")
        assert r.status_code == 200

    def test_carbon_shape(self, client):
        data = client.get("/api/v1/dashboard/carbon").json()
        for key in ("carbon_saved_grams", "energy_saved_kwh", "pipeline_efficiency",
                     "optimization_count"):
            assert key in data, f"Carbon missing: {key}"

    def test_carbon_has_optimizations(self, client):
        data = client.get("/api/v1/dashboard/carbon").json()
        opts = data.get("optimizations", [])
        assert isinstance(opts, list)
        assert len(opts) >= 2

    def test_carbon_optimization_shape(self, client):
        opts = client.get("/api/v1/dashboard/carbon").json()["optimizations"]
        for o in opts:
            assert "suggestion" in o
            assert "estimated_savings_percent" in o
            assert "priority" in o

    def test_carbon_has_waste_sources(self, client):
        data = client.get("/api/v1/dashboard/carbon").json()
        ws = data.get("waste_sources", [])
        assert isinstance(ws, list)
        assert len(ws) >= 1

    def test_carbon_waste_source_shape(self, client):
        ws = client.get("/api/v1/dashboard/carbon").json()["waste_sources"]
        for w in ws:
            assert "source" in w
            assert "waste_percent" in w

    def test_carbon_efficiency_score(self, client):
        data = client.get("/api/v1/dashboard/carbon").json()
        assert "efficiency_score" in data
        assert 0 <= data["efficiency_score"] <= 100


# ═══════════════════════════════════════════════════════════════════════════════
#  Telemetry /metrics/history
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetricsHistory:
    def test_returns_200(self, client):
        r = client.get("/api/v1/telemetry/metrics/history")
        assert r.status_code == 200

    def test_history_is_flat_array(self, client):
        data = client.get("/api/v1/telemetry/metrics/history").json()
        assert isinstance(data, list), "History must be flat array, not wrapped object"

    def test_history_has_items(self, client):
        data = client.get("/api/v1/telemetry/metrics/history").json()
        assert len(data) >= 5

    def test_history_item_shape(self, client):
        item = client.get("/api/v1/telemetry/metrics/history").json()[0]
        for key in ("timestamp", "success_rate", "confidence", "fix_time", "carbon_saved"):
            assert key in item, f"History item missing: {key}"

    def test_history_is_chronological(self, client):
        data = client.get("/api/v1/telemetry/metrics/history").json()
        timestamps = [d["timestamp"] for d in data]
        assert timestamps == sorted(timestamps)


# ═══════════════════════════════════════════════════════════════════════════════
#  Telemetry /reasoning-trees
# ═══════════════════════════════════════════════════════════════════════════════

class TestReasoningTrees:
    def test_returns_200(self, client):
        r = client.get("/api/v1/telemetry/reasoning-trees")
        assert r.status_code == 200

    def test_trees_is_dict_keyed_by_scenario(self, client):
        data = client.get("/api/v1/telemetry/reasoning-trees").json()
        assert isinstance(data, dict), "Reasoning trees must be dict keyed by scenario"
        assert len(data) >= 3

    def test_trees_scenario_keys(self, client):
        data = client.get("/api/v1/telemetry/reasoning-trees").json()
        # Keys match DEMO_REASONING_TREES (not aliased frontend names)
        expected = {"pipeline_failure", "security_vulnerability",
                     "merge_request_opened", "inefficient_pipeline"}
        assert expected.issubset(set(data.keys()))

    def test_trees_each_has_nodes_and_edges(self, client):
        data = client.get("/api/v1/telemetry/reasoning-trees").json()
        for key, tree in data.items():
            assert "nodes" in tree, f"{key} missing nodes"
            assert "edges" in tree, f"{key} missing edges"
            assert len(tree["nodes"]) >= 5


# ═══════════════════════════════════════════════════════════════════════════════
#  Telemetry /learning-curve
# ═══════════════════════════════════════════════════════════════════════════════

class TestLearningCurve:
    def test_returns_200(self, client):
        r = client.get("/api/v1/telemetry/learning-curve")
        assert r.status_code == 200

    def test_curve_is_flat_array(self, client):
        data = client.get("/api/v1/telemetry/learning-curve").json()
        assert isinstance(data, list), "Learning curve must be flat array"

    def test_curve_has_items(self, client):
        data = client.get("/api/v1/telemetry/learning-curve").json()
        assert len(data) >= 15

    def test_curve_item_shape(self, client):
        item = client.get("/api/v1/telemetry/learning-curve").json()[0]
        for key in ("event_number", "success", "confidence", "fix_time", "cumulative_success_rate"):
            assert key in item


# ═══════════════════════════════════════════════════════════════════════════════
#  Telemetry /metrics (system metrics envelope)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystemMetrics:
    def test_returns_200(self, client):
        r = client.get("/api/v1/telemetry/metrics")
        assert r.status_code == 200

    def test_metrics_envelope(self, client):
        data = client.get("/api/v1/telemetry/metrics").json()
        for section in ("system_metrics", "agent_metrics", "learning_metrics", "sustainability_metrics"):
            assert section in data, f"Missing section: {section}"

    def test_system_metrics_fields(self, client):
        sm = client.get("/api/v1/telemetry/metrics").json()["system_metrics"]
        for key in ("success_rate", "avg_fix_time_seconds", "total_workflows",
                     "active_workflows", "avg_confidence"):
            assert key in sm

    def test_learning_metrics_fields(self, client):
        lm = client.get("/api/v1/telemetry/metrics").json()["learning_metrics"]
        for key in ("memory_utilization", "knowledge_reuse_count", "reasoning_depth_avg"):
            assert key in lm

    def test_sustainability_metrics_fields(self, client):
        sus = client.get("/api/v1/telemetry/metrics").json()["sustainability_metrics"]
        for key in ("carbon_score", "energy_saved_kwh", "pipeline_efficiency"):
            assert key in sus


# ═══════════════════════════════════════════════════════════════════════════════
#  Telemetry sub-endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetrySubEndpoints:
    def test_success_rate(self, client):
        data = client.get("/api/v1/telemetry/metrics/success-rate").json()
        assert "success_rate" in data
        assert "total_workflows" in data

    def test_fix_time(self, client):
        data = client.get("/api/v1/telemetry/metrics/fix-time").json()
        assert "avg_fix_time_seconds" in data
        assert "self_correction_rate" in data

    def test_collaboration(self, client):
        data = client.get("/api/v1/telemetry/metrics/collaboration").json()
        assert "collaboration_index" in data

    def test_reasoning_depth(self, client):
        data = client.get("/api/v1/telemetry/metrics/reasoning-depth").json()
        assert "reasoning_depth_avg" in data

    def test_memory_reuse(self, client):
        data = client.get("/api/v1/telemetry/metrics/memory-reuse").json()
        assert "memory_utilization" in data
        assert "knowledge_reuse_count" in data


# ═══════════════════════════════════════════════════════════════════════════════
#  Dashboard /workflows
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardWorkflows:
    def test_returns_200(self, client):
        r = client.get("/api/v1/dashboard/workflows")
        assert r.status_code == 200

    def test_workflows_shape(self, client):
        data = client.get("/api/v1/dashboard/workflows").json()
        assert "workflows" in data
        assert "count" in data
        assert isinstance(data["workflows"], list)


# ═══════════════════════════════════════════════════════════════════════════════
#  Webhook test-trigger with scenario mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebhookScenarioMapping:
    def test_trigger_with_scenario(self, client):
        r = client.post("/api/v1/webhooks/test-trigger",
                        json={"scenario": "pipeline_failure_missing_dep"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "triggered"
        assert data["event_type"] == "pipeline_failure"
        assert data["scenario"] == "pipeline_failure_missing_dep"

    def test_trigger_with_event_type(self, client):
        r = client.post("/api/v1/webhooks/test-trigger",
                        json={"event_type": "security_alert"})
        assert r.status_code == 200
        data = r.json()
        assert data["event_type"] == "security_alert"

    def test_trigger_with_security_scenario(self, client):
        r = client.post("/api/v1/webhooks/test-trigger",
                        json={"scenario": "security_vulnerability"})
        assert r.status_code == 200
        assert r.json()["event_type"] == "security_alert"

    def test_trigger_with_merge_request_scenario(self, client):
        r = client.post("/api/v1/webhooks/test-trigger",
                        json={"scenario": "merge_request_opened"})
        assert r.status_code == 200
        assert r.json()["event_type"] == "merge_request_opened"

    def test_trigger_with_inefficient_pipeline_scenario(self, client):
        r = client.post("/api/v1/webhooks/test-trigger",
                        json={"scenario": "inefficient_pipeline"})
        assert r.status_code == 200
        assert r.json()["event_type"] == "pipeline_success"

    def test_trigger_default_event_type(self, client):
        r = client.post("/api/v1/webhooks/test-trigger", json={})
        assert r.status_code == 200
        assert r.json()["event_type"] == "pipeline_failure"

    def test_trigger_returns_workflow_id(self, client):
        r = client.post("/api/v1/webhooks/test-trigger",
                        json={"scenario": "pipeline_failure_missing_dep"})
        data = r.json()
        assert "workflow_id" in data
        assert data["workflow_id"]  # Not empty
