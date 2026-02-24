"""
AutoForge Dashboard API — Aggregated data endpoints for frontend.
"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(request: Request):
    """Get complete dashboard overview data."""
    brain = request.app.state.brain
    telemetry = request.app.state.telemetry
    memory = request.app.state.memory

    agents = brain.get_agent_registry()
    metrics = await telemetry.get_current_metrics()
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
        "agents": agent_statuses,
        "metrics": {
            "success_rate": metrics.get("success_rate", 0.0),
            "avg_fix_time": metrics.get("avg_fix_time", 0.0),
            "total_workflows": metrics.get("total_workflows", 0),
            "active_workflows": metrics.get("active_workflows", 0),
            "learning_score": metrics.get("learning_score", 0.0),
            "carbon_efficiency": metrics.get("carbon_score", 0.0),
        },
        "recent_workflows": [w.to_summary() for w in recent_workflows],
        "meta_intelligence_score": await telemetry.calculate_meta_intelligence(),
    }


@router.get("/agents")
async def get_dashboard_agents(request: Request):
    """Get detailed agent status cards for the dashboard."""
    brain = request.app.state.brain
    agents = brain.get_agent_registry()

    result = []
    for agent_id, agent in agents.items():
        stats = agent.get_stats()
        result.append({
            "id": agent_id,
            "type": agent.agent_type,
            "status": agent.status,
            "active_tasks": stats.get("active_tasks", 0),
            "completed_tasks": stats.get("completed_tasks", 0),
            "success_rate": stats.get("success_rate", 0.0),
            "avg_execution_time_ms": stats.get("avg_execution_time_ms", 0.0),
            "specialization": getattr(agent, "specialization", "general"),
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
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    curve = await telemetry.get_learning_curve()

    return {
        "learning_curve": curve,
        "memory_utilization": metrics.get("memory_utilization", 0.0),
        "knowledge_reuse_count": metrics.get("knowledge_reuse", 0),
        "reasoning_depth_avg": metrics.get("reasoning_depth", 0.0),
        "meta_intelligence_score": await telemetry.calculate_meta_intelligence(),
    }


@router.get("/carbon")
async def get_carbon_dashboard(request: Request):
    """Get sustainability / carbon-efficiency dashboard data."""
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()

    return {
        "carbon_score": metrics.get("carbon_score", 0.0),
        "energy_saved_kwh": metrics.get("energy_saved", 0.0),
        "pipeline_efficiency": metrics.get("pipeline_efficiency", 0.0),
        "optimization_suggestions": metrics.get("optimizations", 0),
    }
