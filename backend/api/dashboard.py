"""
AutoForge Dashboard API — Aggregated data endpoints for frontend.
"""

from fastapi import APIRouter, Request

from config import settings

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(request: Request):
    """Get complete dashboard overview data."""
    brain = request.app.state.brain
    telemetry = request.app.state.telemetry
    memory = request.app.state.memory

    agents = brain.get_agent_registry()
    metrics = await telemetry.get_current_metrics()
    memory_stats = memory.get_stats()
    recent_workflows = brain.get_workflows(limit=5)

    agent_statuses = []
    for agent_id, agent in agents.items():
        stats = agent.get_stats()
        agent_statuses.append({
            "id": agent_id,
            "type": agent.agent_type,
            "status": agent.status,
            "active_tasks": stats.get("active_tasks", 0),
            "success_rate": stats.get("success_rate", 0.0),
        })

    return {
        "system_status": "operational",
        "demo_mode": settings.DEMO_MODE,
        "agents": agent_statuses,
        "metrics": {
            "success_rate": metrics.get("success_rate", 0.0),
            "avg_fix_time": metrics.get("avg_fix_time", 0.0),
            "total_workflows": metrics.get("total_workflows", 0),
            "active_workflows": metrics.get("active_workflows", 0),
            "learning_score": metrics.get("learning_score", 0.0),
            "carbon_efficiency": metrics.get("carbon_score", 0.0),
            "collaboration_index": metrics.get("collaboration_index", 0.0),
            "reasoning_depth": metrics.get("reasoning_depth", 0.0),
            "self_correction_rate": metrics.get("self_correction_rate", 0.0),
        },
        "memory": {
            "total_experiences": memory_stats.get("total_experiences", 0),
            "total_skills": memory_stats.get("total_skills", 0),
            "semantic_patterns": memory_stats.get("semantic_pattern_categories", 0),
            "cross_agent_shares": memory_stats.get("cross_agent_shares", 0),
            "memory_utilization": memory_stats.get("memory_utilization", 0.0),
        },
        "recent_workflows": [w.to_summary() for w in recent_workflows],
        "meta_intelligence_score": await telemetry.calculate_meta_intelligence(),
    }


@router.get("/activity-feed")
async def get_activity_feed(request: Request, limit: int = 50):
    """Get real-time activity feed for all agents."""
    telemetry = request.app.state.telemetry
    activities = await telemetry.get_activity_feed(limit=limit)

    return {"activities": activities, "count": len(activities)}


@router.get("/reasoning/{workflow_id}")
async def get_workflow_reasoning(workflow_id: str, request: Request):
    """Get full reasoning visualization data for a workflow."""
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        return {"error": f"Workflow {workflow_id} not found"}

    return {
        "workflow_id": workflow_id,
        "reasoning_tree": workflow.reasoning_chain,
        "nodes": workflow.get_reasoning_nodes(),
        "edges": workflow.get_reasoning_edges(),
        "decision_path": workflow.get_decision_path(),
        "confidence_scores": workflow.get_confidence_scores(),
        "shared_context": workflow.shared_context,
    }


@router.get("/demo-mode")
async def get_demo_mode():
    """Check if demo mode is active."""
    return {"demo_mode": settings.DEMO_MODE}


@router.post("/demo-mode")
async def toggle_demo_mode(request: Request):
    """Toggle demo mode at runtime."""
    body = await request.json()
    new_val = body.get("enabled", not settings.DEMO_MODE)
    settings.DEMO_MODE = new_val
    return {"demo_mode": settings.DEMO_MODE}
