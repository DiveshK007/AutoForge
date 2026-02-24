"""
AutoForge Telemetry API — Metrics and observability endpoints.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/metrics")
async def get_system_metrics(request: Request):
    """Get current system-wide telemetry metrics."""
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()

    return {
        "system_metrics": {
            "success_rate": metrics.get("success_rate", 0.0),
            "avg_fix_time_seconds": metrics.get("avg_fix_time", 0.0),
            "total_workflows": metrics.get("total_workflows", 0),
            "active_workflows": metrics.get("active_workflows", 0),
            "total_fixes_applied": metrics.get("total_fixes", 0),
            "avg_confidence": metrics.get("avg_confidence", 0.0),
            "self_correction_rate": metrics.get("self_correction_rate", 0.0),
            "collaboration_index": metrics.get("collaboration_index", 0.0),
        },
        "agent_metrics": metrics.get("agent_metrics", {}),
        "learning_metrics": {
            "memory_utilization": metrics.get("memory_utilization", 0.0),
            "knowledge_reuse_count": metrics.get("knowledge_reuse", 0),
            "policy_confidence_trend": metrics.get("policy_trend", []),
            "reasoning_depth_avg": metrics.get("reasoning_depth", 0.0),
        },
        "sustainability_metrics": {
            "carbon_score": metrics.get("carbon_score", 0.0),
            "energy_saved_kwh": metrics.get("energy_saved", 0.0),
            "pipeline_efficiency": metrics.get("pipeline_efficiency", 0.0),
            "optimization_suggestions": metrics.get("optimizations", 0),
        },
    }


@router.get("/metrics/history")
async def get_metrics_history(request: Request, hours: int = 24):
    """Get historical metrics over time."""
    telemetry = request.app.state.telemetry
    history = await telemetry.get_metrics_history(hours=hours)

    return {"history": history, "period_hours": hours}


@router.get("/metrics/success-rate")
async def get_success_rate(request: Request):
    """Get current workflow success rate."""
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    return {
        "success_rate": metrics.get("success_rate", 0.0),
        "total_workflows": metrics.get("total_workflows", 0),
        "total_fixes": metrics.get("total_fixes", 0),
    }


@router.get("/metrics/fix-time")
async def get_fix_time(request: Request):
    """Get average fix time metrics."""
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    return {
        "avg_fix_time_seconds": metrics.get("avg_fix_time", 0.0),
        "self_correction_rate": metrics.get("self_correction_rate", 0.0),
    }


@router.get("/metrics/collaboration")
async def get_collaboration_metrics(request: Request):
    """Get agent collaboration metrics."""
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    return {
        "collaboration_index": metrics.get("collaboration_index", 0.0),
        "agent_metrics": metrics.get("agent_metrics", {}),
    }


@router.get("/metrics/reasoning-depth")
async def get_reasoning_depth(request: Request):
    """Get average reasoning depth across agents."""
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    return {
        "reasoning_depth_avg": metrics.get("reasoning_depth", 0.0),
        "policy_confidence_trend": metrics.get("policy_trend", []),
    }


@router.get("/metrics/memory-reuse")
async def get_memory_reuse(request: Request):
    """Get memory utilisation and knowledge reuse stats."""
    telemetry = request.app.state.telemetry
    metrics = await telemetry.get_current_metrics()
    return {
        "memory_utilization": metrics.get("memory_utilization", 0.0),
        "knowledge_reuse_count": metrics.get("knowledge_reuse", 0),
    }


@router.get("/reasoning-trees")
async def get_reasoning_trees(request: Request, limit: int = 10):
    """Get recent reasoning trees from all agents."""
    telemetry = request.app.state.telemetry
    trees = await telemetry.get_recent_reasoning_trees(limit=limit)

    return {"reasoning_trees": trees, "count": len(trees)}


@router.get("/learning-curve")
async def get_learning_curve(request: Request):
    """Get learning improvement data over time."""
    telemetry = request.app.state.telemetry
    curve = await telemetry.get_learning_curve()

    return {
        "learning_curve": curve,
        "meta_intelligence_score": await telemetry.calculate_meta_intelligence(),
    }
