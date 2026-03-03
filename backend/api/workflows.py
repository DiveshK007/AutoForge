"""
AutoForge Workflow API — Workflow tracking, management, and demo triggers.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from models.events import EventType, NormalizedEvent
from middleware.auth import AuthContext, get_auth_context, require_role
from logging_config import get_logger

router = APIRouter()
log = get_logger("workflows")

# ── Demo-scenario directory ──────────────────────────────────────
_DEMO_DIR = Path(__file__).resolve().parents[2] / "demo_scenarios"


@router.get("/")
async def list_workflows(request: Request, limit: int = 20, offset: int = 0, _auth: AuthContext = Depends(get_auth_context)):
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
async def get_workflow(workflow_id: str, request: Request, _auth: AuthContext = Depends(get_auth_context)):
    """Get detailed workflow state."""
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    return {
        "workflow": workflow.to_dict(),
        "tasks": [t.to_dict() for t in workflow.tasks],
        "agents_involved": workflow.agents_involved,
        "reasoning_chain": workflow.reasoning_chain,
        "timeline": workflow.get_timeline(),
    }


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str, request: Request, _auth: AuthContext = Depends(require_role("operator"))):
    """Cancel an active workflow."""
    brain = request.app.state.brain
    result = await brain.cancel_workflow(workflow_id)

    return {"workflow_id": workflow_id, "cancelled": result}


@router.get("/{workflow_id}/timeline")
async def get_workflow_timeline(workflow_id: str, request: Request, _auth: AuthContext = Depends(get_auth_context)):
    """Get detailed timeline of a workflow execution."""
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    return {
        "workflow_id": workflow_id,
        "timeline": workflow.get_timeline(),
        "duration_seconds": workflow.duration_seconds,
        "status": workflow.status,
    }


@router.get("/{workflow_id}/reasoning")
async def get_workflow_reasoning(workflow_id: str, request: Request, _auth: AuthContext = Depends(get_auth_context)):
    """Get the full reasoning chain for a workflow."""
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    return {
        "workflow_id": workflow_id,
        "reasoning_chain": workflow.reasoning_chain,
        "tasks": [
            {
                "task_id": t.task_id,
                "agent": t.agent_type,
                "status": t.status,
                "reasoning": getattr(t, "reasoning", None),
                "confidence": getattr(t, "confidence", None),
            }
            for t in workflow.tasks
        ],
    }


@router.get("/{workflow_id}/telemetry")
async def get_workflow_telemetry(workflow_id: str, request: Request, _auth: AuthContext = Depends(get_auth_context)):
    """Get telemetry snapshot scoped to a single workflow."""
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    return {
        "workflow_id": workflow_id,
        "status": workflow.status,
        "duration_seconds": workflow.duration_seconds,
        "agents_involved": workflow.agents_involved,
        "task_count": len(workflow.tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "agent": t.agent_type,
                "status": t.status,
                "execution_time_ms": getattr(t, "execution_time_ms", None),
            }
            for t in workflow.tasks
        ],
    }


# ── Demo endpoints ───────────────────────────────────────────────

@router.get("/demo/scenarios")
async def list_demo_scenarios(_auth: AuthContext = Depends(get_auth_context)):
    """List available demo scenarios."""
    scenarios = []
    if _DEMO_DIR.exists():
        for p in sorted(_DEMO_DIR.glob("*.json")):
            try:
                data = json.loads(p.read_text())
                scenarios.append({
                    "id": p.stem,
                    "name": data.get("name", p.stem),
                    "description": data.get("description", ""),
                    "event_type": data.get("event_type", ""),
                })
            except Exception:
                continue
    return {"scenarios": scenarios, "count": len(scenarios)}


@router.post("/demo/run/{scenario_id}")
async def run_demo_scenario(scenario_id: str, request: Request, _auth: AuthContext = Depends(require_role("operator"))):
    """
    Trigger a demo scenario by name (stem of the JSON file).

    Example: ``POST /demo/run/pipeline_failure_missing_dep``
    """
    brain = request.app.state.brain

    scenario_file = _DEMO_DIR / f"{scenario_id}.json"
    if not scenario_file.exists():
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    data = json.loads(scenario_file.read_text())
    payload = data.get("payload", {})

    event = NormalizedEvent(
        event_type=EventType(data.get("event_type", "pipeline_failure")),
        source="demo_scenario",
        project_id=payload.get("project_id", "demo-project-1"),
        project_name=payload.get("project_name", "demo"),
        ref=payload.get("ref", "main"),
        payload=payload,
        metadata={"scenario": scenario_id, "demo": True},
        timestamp=datetime.now(timezone.utc),
    )

    workflow_id = await brain.ingest_event(event)

    return {
        "status": "triggered",
        "scenario": scenario_id,
        "scenario_name": data.get("name", scenario_id),
        "workflow_id": workflow_id,
        "event_type": event.event_type.value,
    }


# ─── Celery Result Tracking ─────────────────────────────────────

@router.get("/celery-status/{celery_task_id}")
async def celery_task_status(celery_task_id: str, _auth: AuthContext = Depends(get_auth_context)):
    """
    Query the status and result of a Celery-dispatched task.

    Returns task state (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
    and the result payload when complete.
    """
    try:
        from worker import celery_app
        result = celery_app.AsyncResult(celery_task_id)

        response = {
            "celery_task_id": celery_task_id,
            "state": result.state,
            "ready": result.ready(),
        }

        if result.ready():
            if result.successful():
                response["result"] = result.result
                response["status"] = "success"
            else:
                response["status"] = "failed"
                response["error"] = str(result.result) if result.result else "Unknown error"
        elif result.state == "STARTED":
            response["status"] = "running"
            response["info"] = result.info if isinstance(result.info, dict) else {}
        elif result.state == "RETRY":
            response["status"] = "retrying"
            response["info"] = result.info if isinstance(result.info, dict) else {}
        else:
            response["status"] = "pending"

        return response

    except Exception as exc:
        log.warning("celery_status_check_failed", task_id=celery_task_id, error=str(exc))
        return {
            "celery_task_id": celery_task_id,
            "state": "UNKNOWN",
            "status": "error",
            "error": f"Cannot query Celery: {exc}",
        }
