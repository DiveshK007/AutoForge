"""
AutoForge Approval API — Human-in-the-Loop approval gate for high-risk tasks.

Provides:
- GET  /pending          — list tasks awaiting approval
- POST /{approval_id}/approve  — approve a pending task
- POST /{approval_id}/reject   — reject a pending task
- GET  /history          — recent approval decisions
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from logging_config import get_logger
from middleware.auth import AuthContext, get_auth_context, require_role

log = get_logger("approvals")

router = APIRouter()


# ─── In-Memory Approval Queue ───────────────────────────────────

class ApprovalRequest:
    """A task waiting for human approval."""

    def __init__(
        self,
        task_id: str,
        workflow_id: str,
        agent_type: str,
        action: str,
        reason: str,
        risk_score: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.approval_id = str(uuid4())[:12]
        self.task_id = task_id
        self.workflow_id = workflow_id
        self.agent_type = agent_type
        self.action = action
        self.reason = reason
        self.risk_score = risk_score
        self.context = context or {}
        self.created_at = datetime.now(timezone.utc)
        self.status: str = "pending"  # pending | approved | rejected
        self.decided_at: Optional[datetime] = None
        self.decided_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "agent_type": self.agent_type,
            "action": self.action,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "context": self.context,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decided_by": self.decided_by,
        }


class ApprovalQueue:
    """Singleton in-memory approval queue."""

    def __init__(self):
        self._pending: Dict[str, ApprovalRequest] = {}
        self._history: List[ApprovalRequest] = []

    def submit(self, req: ApprovalRequest) -> str:
        """Submit a task for approval. Returns approval_id."""
        self._pending[req.approval_id] = req
        log.info(
            "approval_submitted",
            approval_id=req.approval_id,
            task_id=req.task_id,
            action=req.action,
            reason=req.reason,
        )
        return req.approval_id

    def get_pending(self) -> List[Dict[str, Any]]:
        """List all pending approval requests."""
        return [r.to_dict() for r in self._pending.values()]

    def approve(self, approval_id: str, approved_by: str = "admin") -> ApprovalRequest:
        """Approve a pending request."""
        req = self._pending.pop(approval_id, None)
        if not req:
            raise KeyError(f"Approval {approval_id} not found or already decided")
        req.status = "approved"
        req.decided_at = datetime.now(timezone.utc)
        req.decided_by = approved_by
        self._history.append(req)
        log.info("approval_approved", approval_id=approval_id, approved_by=approved_by)
        return req

    def reject(self, approval_id: str, rejected_by: str = "admin") -> ApprovalRequest:
        """Reject a pending request."""
        req = self._pending.pop(approval_id, None)
        if not req:
            raise KeyError(f"Approval {approval_id} not found or already decided")
        req.status = "rejected"
        req.decided_at = datetime.now(timezone.utc)
        req.decided_by = rejected_by
        self._history.append(req)
        log.info("approval_rejected", approval_id=approval_id, rejected_by=rejected_by)
        return req

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Recent approval decisions."""
        return [r.to_dict() for r in self._history[-limit:]]

    @property
    def pending_count(self) -> int:
        return len(self._pending)


# Global singleton
approval_queue = ApprovalQueue()


# ─── Request/Response Models ────────────────────────────────────

class ApprovalDecision(BaseModel):
    decided_by: str = "admin"


# ─── API Endpoints ──────────────────────────────────────────────

@router.get("/pending")
async def list_pending_approvals(_auth: AuthContext = Depends(get_auth_context)):
    """List all tasks awaiting human approval."""
    return {
        "pending": approval_queue.get_pending(),
        "count": approval_queue.pending_count,
    }


@router.post("/{approval_id}/approve")
async def approve_task(approval_id: str, body: ApprovalDecision = ApprovalDecision(), _auth: AuthContext = Depends(require_role("operator"))):
    """Approve a pending task — it will proceed to execution."""
    try:
        req = approval_queue.approve(approval_id, approved_by=body.decided_by)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")

    # Broadcast approval via WebSocket
    try:
        from api.websocket import broadcast_activity
        await broadcast_activity(
            "approval_granted",
            f"Task {req.action} on workflow {req.workflow_id[:8]} approved by {req.decided_by}",
            agent=req.agent_type,
            status="approved",
        )
    except Exception:
        pass

    return {
        "status": "approved",
        "approval_id": approval_id,
        "task_id": req.task_id,
        "workflow_id": req.workflow_id,
    }


@router.post("/{approval_id}/reject")
async def reject_task(approval_id: str, body: ApprovalDecision = ApprovalDecision(), _auth: AuthContext = Depends(require_role("operator"))):
    """Reject a pending task — it will be skipped."""
    try:
        req = approval_queue.reject(approval_id, rejected_by=body.decided_by)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")

    # Broadcast rejection via WebSocket
    try:
        from api.websocket import broadcast_activity
        await broadcast_activity(
            "approval_rejected",
            f"Task {req.action} on workflow {req.workflow_id[:8]} rejected by {req.decided_by}",
            agent=req.agent_type,
            status="rejected",
        )
    except Exception:
        pass

    return {
        "status": "rejected",
        "approval_id": approval_id,
        "task_id": req.task_id,
        "workflow_id": req.workflow_id,
    }


@router.get("/history")
async def approval_history(limit: int = 50, _auth: AuthContext = Depends(get_auth_context)):
    """Get recent approval decisions."""
    return {
        "history": approval_queue.get_history(limit),
        "total_decided": len(approval_queue._history),
        "pending_count": approval_queue.pending_count,
    }
