"""
AutoForge Dashboard API — Aggregated data endpoints for frontend.

Provides all data the Next.js dashboard consumes, including
demo-mode precomputed state for impressive first-load experience.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from demo.engine import (
    DEMO_REASONING_TREES,
    DEMO_ENERGY_ESTIMATES,
    get_demo_scenario,
)

router = APIRouter()

# ─── Precomputed demo data shown on first load (DEMO_MODE) ──────────────────

_DEMO_AGENTS: List[Dict[str, Any]] = [
    {"name": "SRE Agent", "type": "sre", "status": "active", "tasks_completed": 42, "success_rate": 0.94, "avg_confidence": 0.91},
    {"name": "Security Agent", "type": "security", "status": "active", "tasks_completed": 38, "success_rate": 0.97, "avg_confidence": 0.93},
    {"name": "QA Agent", "type": "qa", "status": "active", "tasks_completed": 55, "success_rate": 0.92, "avg_confidence": 0.89},
    {"name": "Review Agent", "type": "review", "status": "idle", "tasks_completed": 27, "success_rate": 0.88, "avg_confidence": 0.85},
    {"name": "Docs Agent", "type": "docs", "status": "idle", "tasks_completed": 19, "success_rate": 0.95, "avg_confidence": 0.90},
    {"name": "GreenOps Agent", "type": "greenops", "status": "active", "tasks_completed": 31, "success_rate": 0.90, "avg_confidence": 0.87},
]

_DEMO_METRICS: Dict[str, Any] = {
    "success_rate": 0.926,
    "avg_fix_time": 12.4,
    "avg_confidence": 0.89,
    "total_events": 212,
    "avg_reasoning_depth": 4.3,
    "collaboration_index": 0.78,
    "self_correction_rate": 0.34,
    "carbon_saved_grams": 18.72,
}

_DEMO_ACTIVITY: List[Dict[str, Any]] = [
    {"timestamp": "2025-01-15T14:32:00Z", "type": "workflow_completed", "agent": "sre", "description": "Pipeline failure resolved — numpy dependency restored", "status": "completed", "workflow_id": "wf-demo-001"},
    {"timestamp": "2025-01-15T14:30:15Z", "type": "task_completed", "agent": "security", "description": "Security scan passed — no new CVEs detected", "status": "completed", "workflow_id": "wf-demo-001"},
    {"timestamp": "2025-01-15T14:29:42Z", "type": "task_completed", "agent": "qa", "description": "Generated 3 regression tests for numpy usage", "status": "completed", "workflow_id": "wf-demo-001"},
    {"timestamp": "2025-01-15T14:28:10Z", "type": "task_started", "agent": "greenops", "description": "Pipeline efficiency audit started", "status": "running", "workflow_id": "wf-demo-001"},
    {"timestamp": "2025-01-15T14:27:00Z", "type": "workflow_created", "agent": None, "description": "New workflow: pipeline_failure in project ml-api", "status": "pending", "workflow_id": "wf-demo-001"},
    {"timestamp": "2025-01-15T14:15:00Z", "type": "workflow_completed", "agent": "security", "description": "CVE-2020-28500 in lodash patched → 4.17.21", "status": "completed", "workflow_id": "wf-demo-002"},
    {"timestamp": "2025-01-15T14:10:00Z", "type": "self_correction", "agent": "sre", "description": "Self-corrected after first fix attempt — adjusted version pin", "status": "completed", "workflow_id": "wf-demo-003"},
    {"timestamp": "2025-01-15T14:05:00Z", "type": "task_completed", "agent": "review", "description": "Code review posted — 3 issues, quality score 72%", "status": "completed", "workflow_id": "wf-demo-004"},
    {"timestamp": "2025-01-15T14:00:00Z", "type": "task_completed", "agent": "docs", "description": "Changelog updated with dependency fix details", "status": "completed", "workflow_id": "wf-demo-001"},
    {"timestamp": "2025-01-15T13:55:00Z", "type": "knowledge_share", "agent": "greenops", "description": "Shared pipeline optimization insights with SRE agent", "status": "completed"},
]

_DEMO_METRICS_HISTORY: List[Dict[str, Any]] = [
    {"timestamp": "2025-01-15T10:00:00Z", "success_rate": 0.80, "confidence": 0.75, "fix_time": 22.1, "carbon_saved": 1.2},
    {"timestamp": "2025-01-15T10:30:00Z", "success_rate": 0.82, "confidence": 0.78, "fix_time": 20.5, "carbon_saved": 2.4},
    {"timestamp": "2025-01-15T11:00:00Z", "success_rate": 0.85, "confidence": 0.81, "fix_time": 18.3, "carbon_saved": 4.1},
    {"timestamp": "2025-01-15T11:30:00Z", "success_rate": 0.86, "confidence": 0.83, "fix_time": 16.7, "carbon_saved": 5.8},
    {"timestamp": "2025-01-15T12:00:00Z", "success_rate": 0.88, "confidence": 0.85, "fix_time": 15.2, "carbon_saved": 8.2},
    {"timestamp": "2025-01-15T12:30:00Z", "success_rate": 0.89, "confidence": 0.86, "fix_time": 14.1, "carbon_saved": 10.5},
    {"timestamp": "2025-01-15T13:00:00Z", "success_rate": 0.90, "confidence": 0.87, "fix_time": 13.5, "carbon_saved": 13.1},
    {"timestamp": "2025-01-15T13:30:00Z", "success_rate": 0.91, "confidence": 0.88, "fix_time": 12.9, "carbon_saved": 15.6},
    {"timestamp": "2025-01-15T14:00:00Z", "success_rate": 0.92, "confidence": 0.89, "fix_time": 12.4, "carbon_saved": 18.7},
]

_DEMO_LEARNING_CURVE: List[Dict[str, Any]] = [
    {"event_number": 1, "success": True, "confidence": 0.72, "fix_time": 25.3, "cumulative_success_rate": 1.0},
    {"event_number": 2, "success": False, "confidence": 0.65, "fix_time": 30.1, "cumulative_success_rate": 0.50},
    {"event_number": 3, "success": True, "confidence": 0.78, "fix_time": 20.5, "cumulative_success_rate": 0.67},
    {"event_number": 4, "success": True, "confidence": 0.80, "fix_time": 18.2, "cumulative_success_rate": 0.75},
    {"event_number": 5, "success": True, "confidence": 0.82, "fix_time": 16.5, "cumulative_success_rate": 0.80},
    {"event_number": 6, "success": False, "confidence": 0.70, "fix_time": 22.0, "cumulative_success_rate": 0.67},
    {"event_number": 7, "success": True, "confidence": 0.85, "fix_time": 14.3, "cumulative_success_rate": 0.71},
    {"event_number": 8, "success": True, "confidence": 0.87, "fix_time": 13.1, "cumulative_success_rate": 0.75},
    {"event_number": 9, "success": True, "confidence": 0.88, "fix_time": 12.8, "cumulative_success_rate": 0.78},
    {"event_number": 10, "success": True, "confidence": 0.90, "fix_time": 12.0, "cumulative_success_rate": 0.80},
    {"event_number": 11, "success": True, "confidence": 0.91, "fix_time": 11.5, "cumulative_success_rate": 0.82},
    {"event_number": 12, "success": True, "confidence": 0.89, "fix_time": 12.4, "cumulative_success_rate": 0.83},
    {"event_number": 13, "success": True, "confidence": 0.92, "fix_time": 11.0, "cumulative_success_rate": 0.85},
    {"event_number": 14, "success": True, "confidence": 0.93, "fix_time": 10.8, "cumulative_success_rate": 0.86},
    {"event_number": 15, "success": False, "confidence": 0.75, "fix_time": 18.0, "cumulative_success_rate": 0.80},
    {"event_number": 16, "success": True, "confidence": 0.91, "fix_time": 11.2, "cumulative_success_rate": 0.81},
    {"event_number": 17, "success": True, "confidence": 0.92, "fix_time": 10.5, "cumulative_success_rate": 0.82},
    {"event_number": 18, "success": True, "confidence": 0.93, "fix_time": 10.1, "cumulative_success_rate": 0.83},
    {"event_number": 19, "success": True, "confidence": 0.94, "fix_time": 9.8, "cumulative_success_rate": 0.84},
    {"event_number": 20, "success": True, "confidence": 0.93, "fix_time": 10.0, "cumulative_success_rate": 0.85},
]


def _build_demo_reasoning_visualization(scenario_key: str) -> Dict[str, Any]:
    """Build a rich reasoning tree visualization from a demo scenario."""
    scenario = DEMO_REASONING_TREES.get(scenario_key, {})
    if not scenario:
        return {"nodes": [], "edges": []}

    nodes = []
    edges = []
    node_idx = 0

    # Event trigger node
    nodes.append({"id": f"n{node_idx}", "label": f"Event: {scenario_key.replace('_', ' ').title()}", "type": "event", "confidence": 1.0})
    event_id = f"n{node_idx}"
    node_idx += 1

    # Perception node
    nodes.append({"id": f"n{node_idx}", "label": "Perceive & classify event", "type": "perception", "confidence": 0.98})
    edges.append({"source": event_id, "target": f"n{node_idx}", "label": "ingest"})
    perception_id = f"n{node_idx}"
    node_idx += 1

    # Hypothesis nodes
    hyps = scenario.get("hypotheses", [])[:4]
    hyp_ids = []
    for h in hyps:
        nid = f"n{node_idx}"
        nodes.append({
            "id": nid,
            "label": h["description"][:80],
            "type": "hypothesis",
            "confidence": h.get("probability", 0.5),
        })
        edges.append({"source": perception_id, "target": nid, "label": f"p={h.get('probability', 0):.0%}"})
        hyp_ids.append(nid)
        node_idx += 1

    # Reasoning / selection node
    selected = scenario.get("selected_hypothesis", 0)
    nodes.append({"id": f"n{node_idx}", "label": f"Selected: {scenario.get('root_cause', '')[:60]}", "type": "reasoning", "confidence": scenario.get("confidence", 0.9)})
    reasoning_id = f"n{node_idx}"
    for hid in hyp_ids:
        edges.append({"source": hid, "target": reasoning_id, "label": "evaluate"})
    node_idx += 1

    # Plan node
    plan = scenario.get("plan", {})
    nodes.append({"id": f"n{node_idx}", "label": plan.get("chosen_action", "Execute plan")[:80], "type": "plan", "confidence": plan.get("confidence", 0.9)})
    plan_id = f"n{node_idx}"
    edges.append({"source": reasoning_id, "target": plan_id, "label": "plan"})
    node_idx += 1

    # Action node
    fix = scenario.get("fix_result", {})
    action_label = fix.get("fix_description", plan.get("chosen_action", "Apply fix"))[:80]
    nodes.append({"id": f"n{node_idx}", "label": action_label, "type": "action", "confidence": scenario.get("confidence", 0.9)})
    action_id = f"n{node_idx}"
    edges.append({"source": plan_id, "target": action_id, "label": "execute"})
    node_idx += 1

    # Reflection node
    refl = scenario.get("reflection", {})
    nodes.append({"id": f"n{node_idx}", "label": refl.get("outcome", "Reflect on outcome")[:80], "type": "reflection", "confidence": refl.get("confidence", 0.95)})
    refl_id = f"n{node_idx}"
    edges.append({"source": action_id, "target": refl_id, "label": "reflect"})
    node_idx += 1

    # Result node
    nodes.append({"id": f"n{node_idx}", "label": f"✅ Skill extracted: {refl.get('extracted_skill', 'n/a')}", "type": "result", "confidence": refl.get("confidence", 0.95)})
    edges.append({"source": refl_id, "target": f"n{node_idx}", "label": "learn"})

    return {"nodes": nodes, "edges": edges}


def _demo_reasoning_trees() -> Dict[str, Dict[str, Any]]:
    """Build all demo reasoning trees keyed by scenario."""
    return {key: _build_demo_reasoning_visualization(key) for key in DEMO_REASONING_TREES}


@router.get("/overview")
async def get_dashboard_overview(request: Request):
    """Get complete dashboard overview data — with rich demo state on first load."""
    brain = request.app.state.brain
    telemetry = request.app.state.telemetry
    memory = request.app.state.memory

    agents = brain.get_agent_registry()
    metrics = await telemetry.get_current_metrics()
    recent_workflows = brain.get_workflows(limit=5)

    from config import settings

    # In demo mode with no real workflows yet, return rich precomputed data
    use_demo = settings.DEMO_MODE

    if use_demo:
        return {
            "system_status": "operational",
            "total_workflows": 20,
            "active_workflows": 1,
            "success_rate": _DEMO_METRICS["success_rate"],
            "agents": _DEMO_AGENTS,
            "metrics": _DEMO_METRICS,
            "meta_intelligence_score": 76.8,
        }

    # Live data
    agent_statuses = []
    for agent_id, agent in agents.items():
        stats = agent.get_stats()
        agent_statuses.append({
            "name": agent_id.upper() + " Agent",
            "type": agent.agent_type,
            "status": agent.status,
            "tasks_completed": stats.get("completed_tasks", stats.get("total_completed", 0)),
            "success_rate": stats.get("success_rate", 0.0),
            "avg_confidence": stats.get("avg_confidence", 0.0),
        })

    total_wf = metrics.get("total_workflows", 0)
    active_wf = metrics.get("active_workflows", 0)

    return {
        "system_status": "operational",
        "total_workflows": total_wf,
        "active_workflows": active_wf,
        "success_rate": metrics.get("success_rate", 0.0),
        "agents": agent_statuses,
        "metrics": {
            "success_rate": metrics.get("success_rate", 0.0),
            "avg_fix_time": metrics.get("avg_fix_time", 0.0),
            "avg_confidence": metrics.get("avg_confidence", 0.0),
            "total_events": total_wf,
            "avg_reasoning_depth": metrics.get("reasoning_depth", 0.0),
            "collaboration_index": metrics.get("collaboration_index", 0.0),
            "self_correction_rate": metrics.get("self_correction_rate", 0.0),
            "carbon_saved_grams": metrics.get("energy_saved", 0.0) * 475,  # grams CO2 per kWh
        },
        "recent_workflows": [w.to_summary() for w in recent_workflows],
        "meta_intelligence_score": await telemetry.calculate_meta_intelligence() * 100,
    }


@router.get("/agents")
async def get_dashboard_agents(request: Request):
    """Get detailed agent status cards for the dashboard."""
    from config import settings

    brain = request.app.state.brain
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    use_demo = settings.DEMO_MODE

    if use_demo:
        return {"agents": _DEMO_AGENTS, "count": len(_DEMO_AGENTS)}

    agents = brain.get_agent_registry()
    result = []
    for agent_id, agent in agents.items():
        stats = agent.get_stats()
        result.append({
            "name": agent_id.upper() + " Agent",
            "type": agent.agent_type,
            "status": agent.status,
            "tasks_completed": stats.get("completed_tasks", stats.get("total_completed", 0)),
            "success_rate": stats.get("success_rate", 0.0),
            "avg_confidence": stats.get("avg_confidence", 0.0),
        })

    return {"agents": result, "count": len(result)}


@router.get("/workflows")
async def get_dashboard_workflows(request: Request, limit: int = 20, status: str | None = None):
    """Get workflow list for the dashboard, optionally filtered by status."""
    brain = request.app.state.brain
    workflows = brain.get_workflows(limit=limit)

    items = []
    for w in workflows:
        summary = w.to_summary()
        if status and str(summary.get("status", "")) != status:
            continue
        items.append(summary)

    return {"workflows": items, "count": len(items)}


@router.get("/activity")
async def get_activity_feed_compat(request: Request, limit: int = 50):
    """Activity feed (frontend-compatible path)."""
    return await get_activity_feed(request, limit=limit)


@router.get("/activity-feed")
async def get_activity_feed(request: Request, limit: int = 50):
    """Get real-time activity feed for all agents."""
    from config import settings

    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    use_demo = settings.DEMO_MODE

    if use_demo:
        return _DEMO_ACTIVITY[:limit]

    activities = await telemetry.get_activity_feed(limit=limit)
    # Flatten to array for frontend
    return [
        {
            "timestamp": a.get("timestamp", ""),
            "type": a.get("event", ""),
            "agent": a.get("detail", "").split(":")[0] if ":" in a.get("detail", "") else None,
            "description": a.get("detail", a.get("event", "")),
            "status": "completed",
        }
        for a in activities
    ]


# Alias map: frontend scenario names → DEMO_REASONING_TREES keys
_SCENARIO_ALIASES: Dict[str, str] = {
    "pipeline_failure_missing_dep": "pipeline_failure",
    "security_vulnerability": "security_vulnerability",
    "merge_request_opened": "merge_request_opened",
    "inefficient_pipeline": "inefficient_pipeline",
}


@router.get("/reasoning/{workflow_id}")
async def get_workflow_reasoning(workflow_id: str, request: Request):
    """Get full reasoning visualization data for a workflow."""
    from config import settings

    brain = request.app.state.brain

    # Resolve alias (frontend scenario name → demo tree key)
    resolved = _SCENARIO_ALIASES.get(workflow_id, workflow_id)

    # Demo mode: if workflow_id matches a scenario key, return precomputed tree
    if settings.DEMO_MODE and resolved in DEMO_REASONING_TREES:
        viz = _build_demo_reasoning_visualization(resolved)
        return {
            "workflow_id": workflow_id,
            "nodes": viz["nodes"],
            "edges": viz["edges"],
        }

    workflow = brain.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    return {
        "workflow_id": workflow_id,
        "reasoning_tree": workflow.reasoning_chain,
        "nodes": workflow.get_reasoning_nodes(),
        "edges": workflow.get_reasoning_edges(),
        "decision_path": workflow.get_decision_path(),
        "confidence_scores": workflow.get_confidence_scores(),
    }


@router.get("/learning")
async def get_learning_dashboard(request: Request):
    """Get learning / knowledge-reuse dashboard data."""
    from config import settings

    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    use_demo = settings.DEMO_MODE

    if use_demo:
        return {
            "learning_curve": _DEMO_LEARNING_CURVE,
            "memory_utilization": 0.73,
            "knowledge_reuse_count": 47,
            "reasoning_depth_avg": 4.3,
            "meta_intelligence_score": 76.8,
        }

    curve = await telemetry.get_learning_curve()
    return {
        "learning_curve": curve,
        "memory_utilization": metrics.get("memory_utilization", 0.0),
        "knowledge_reuse_count": metrics.get("knowledge_reuse", 0),
        "reasoning_depth_avg": metrics.get("reasoning_depth", 0.0),
        "meta_intelligence_score": await telemetry.calculate_meta_intelligence() * 100,
    }


@router.get("/carbon")
async def get_carbon_dashboard(request: Request):
    """Get sustainability / carbon-efficiency dashboard data."""
    from config import settings

    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    use_demo = settings.DEMO_MODE

    if use_demo:
        return {
            "carbon_saved_grams": 18.72,
            "energy_saved_kwh": 0.0394,
            "pipeline_efficiency": 87.5,
            "optimization_count": 9,
            "trees_equivalent": 0.00089,
            "efficiency_score": 85,
            "optimizations": DEMO_ENERGY_ESTIMATES.get("pipeline_failure", {}).get("optimizations", []),
            "waste_sources": DEMO_ENERGY_ESTIMATES.get("pipeline_failure", {}).get("waste_sources", []),
        }

    return {
        "carbon_saved_grams": metrics.get("energy_saved", 0.0) * 475,
        "energy_saved_kwh": metrics.get("energy_saved", 0.0),
        "pipeline_efficiency": metrics.get("pipeline_efficiency", 0.0),
        "optimization_count": metrics.get("optimizations", 0),
    }


# ─── Retry Timeline Endpoint ────────────────────────────────────────

_DEMO_RETRIES = [
    {"attempt": 1, "maxAttempts": 3, "agent": "sre", "strategy": "Original diagnosis — missing dependency", "outcome": "failure", "confidence": 0.45, "duration_ms": 1200},
    {"attempt": 2, "maxAttempts": 3, "agent": "sre", "strategy": "Alternate fix — pin exact version numpy==1.24.4", "outcome": "failure", "confidence": 0.62, "duration_ms": 800},
    {"attempt": 3, "maxAttempts": 3, "agent": "sre", "strategy": "Reflection-based — update requirements.txt with range constraint", "outcome": "success", "confidence": 0.91, "duration_ms": 950},
]


@router.get("/retries/{workflow_id}")
async def get_workflow_retries(workflow_id: str, request: Request):
    """Get retry / self-correction history for a workflow."""
    from config import settings

    brain = request.app.state.brain

    if settings.DEMO_MODE:
        return {"workflow_id": workflow_id, "retries": _DEMO_RETRIES}

    retries = brain.get_retry_history(workflow_id)
    return {"workflow_id": workflow_id, "retries": retries}


# ─── Agent Communication Endpoint ───────────────────────────────

_DEMO_COMM_DATA = {
    "agents": ["sre", "security", "qa", "review", "docs", "greenops"],
    "links": [
        {"from": "sre", "to": "security", "dataType": "fix_patch", "volume": 0.9},
        {"from": "sre", "to": "qa", "dataType": "fix_branch", "volume": 0.85},
        {"from": "sre", "to": "greenops", "dataType": "pipeline_data", "volume": 0.5},
        {"from": "security", "to": "review", "dataType": "scan_result", "volume": 0.7},
        {"from": "security", "to": "qa", "dataType": "vuln_context", "volume": 0.4},
        {"from": "qa", "to": "review", "dataType": "test_results", "volume": 0.8},
        {"from": "qa", "to": "docs", "dataType": "coverage_report", "volume": 0.5},
        {"from": "review", "to": "docs", "dataType": "review_notes", "volume": 0.75},
        {"from": "greenops", "to": "review", "dataType": "energy_report", "volume": 0.6},
    ],
    "context": {
        "sre": {"root_cause": "missing numpy dependency", "fix_branch": "autoforge/fix-pipeline-abc123", "confidence": 0.92},
        "security": {"scan_result": "clean", "cve_count": 0},
        "qa": {"tests_generated": 3, "coverage_delta": "+4.2%"},
        "greenops": {"energy_kwh": 0.0108, "carbon_kg": 0.000005},
    },
}


@router.get("/communication/{workflow_id}")
async def get_agent_communication(workflow_id: str, request: Request):
    """Get agent-to-agent communication graph data for a workflow."""
    from config import settings

    brain = request.app.state.brain

    if settings.DEMO_MODE:
        return {"workflow_id": workflow_id, **_DEMO_COMM_DATA}

    comm = brain.get_agent_communication(workflow_id)
    return {"workflow_id": workflow_id, **comm}
