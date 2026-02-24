"""
AutoForge Workflow API — Workflow tracking and management.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def list_workflows(request: Request, limit: int = 20, offset: int = 0):
    """List all workflows with pagination."""
    brain = request.app.state.brain
    workflows = brain.get_workflows(limit=limit, offset=offset)

    return {
        "workflows": [w.to_dict() for w in workflows],
        "total": brain.get_workflow_count(),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request):
    """Get detailed workflow state."""
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        return {"error": f"Workflow {workflow_id} not found"}

    return {
        "workflow": workflow.to_dict(),
        "tasks": [t.to_dict() for t in workflow.tasks],
        "agents_involved": workflow.agents_involved,
        "reasoning_chain": workflow.reasoning_chain,
        "timeline": workflow.get_timeline(),
    }


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str, request: Request):
    """Cancel an active workflow."""
    brain = request.app.state.brain
    result = await brain.cancel_workflow(workflow_id)

    return {"workflow_id": workflow_id, "cancelled": result}


@router.get("/{workflow_id}/timeline")
async def get_workflow_timeline(workflow_id: str, request: Request):
    """Get detailed timeline of a workflow execution."""
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        return {"error": f"Workflow {workflow_id} not found"}

    return {
        "workflow_id": workflow_id,
        "timeline": workflow.get_timeline(),
        "duration_seconds": workflow.duration_seconds,
        "status": workflow.status,
    }
