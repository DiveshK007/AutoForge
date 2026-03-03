"""
AutoForge Agent API — Agent status and control endpoints.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from middleware.auth import AuthContext, get_auth_context

router = APIRouter()


class AgentStatusResponse(BaseModel):
    agent_id: str
    agent_type: str
    status: str
    active_tasks: int
    total_completed: int
    success_rate: float
    avg_confidence: float
    last_active: Optional[str] = None


@router.get("/")
async def list_agents(request: Request, _auth: AuthContext = Depends(get_auth_context)):
    """List all registered agents and their current status."""
    brain = request.app.state.brain
    agents = brain.get_agent_registry()

    agent_list = []
    for agent_id, agent in agents.items():
        stats = agent.get_stats()
        agent_list.append(
            AgentStatusResponse(
                agent_id=agent_id,
                agent_type=agent.agent_type,
                status=agent.status,
                active_tasks=stats.get("active_tasks", 0),
                total_completed=stats.get("total_completed", 0),
                success_rate=stats.get("success_rate", 0.0),
                avg_confidence=stats.get("avg_confidence", 0.0),
                last_active=stats.get("last_active"),
            )
        )

    return {"agents": agent_list, "total": len(agent_list)}


@router.get("/{agent_id}")
async def get_agent_detail(agent_id: str, request: Request, _auth: AuthContext = Depends(get_auth_context)):
    """Get detailed status for a specific agent."""
    brain = request.app.state.brain
    agent = brain.get_agent(agent_id)

    if not agent:
        return {"error": f"Agent {agent_id} not found"}

    return {
        "agent_id": agent_id,
        "agent_type": agent.agent_type,
        "status": agent.status,
        "stats": agent.get_stats(),
        "capabilities": agent.capabilities,
        "active_reasoning": agent.get_active_reasoning(),
        "recent_actions": agent.get_recent_actions(limit=10),
    }


@router.get("/{agent_id}/reasoning")
async def get_agent_reasoning(agent_id: str, request: Request, _auth: AuthContext = Depends(get_auth_context)):
    """Get the reasoning tree for an agent's current or last task."""
    brain = request.app.state.brain
    agent = brain.get_agent(agent_id)

    if not agent:
        return {"error": f"Agent {agent_id} not found"}

    return {
        "agent_id": agent_id,
        "reasoning_tree": agent.get_reasoning_tree(),
        "hypotheses": agent.get_hypotheses(),
        "decision_path": agent.get_decision_path(),
    }
