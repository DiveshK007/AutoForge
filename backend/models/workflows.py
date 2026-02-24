"""
AutoForge Workflow Models — Workflow state and task tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow lifecycle states."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Individual task states."""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(str, Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentTask(BaseModel):
    """A task assigned to a specific agent."""
    task_id: str = Field(default_factory=lambda: str(uuid4())[:12])
    workflow_id: str
    agent_type: str
    action: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.QUEUED
    dependencies: List[str] = []  # task_ids this task depends on (DAG edges)
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    reasoning: Dict[str, Any] = {}
    confidence: float = 0.0
    risk_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "agent_type": self.agent_type,
            "action": self.action,
            "priority": self.priority.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


class TimelineEntry(BaseModel):
    """A single entry in the workflow timeline."""
    timestamp: datetime
    event: str
    agent: Optional[str] = None
    detail: str = ""
    confidence: Optional[float] = None


class Workflow(BaseModel):
    """Complete workflow tracking a multi-agent remediation cycle."""
    workflow_id: str = Field(default_factory=lambda: str(uuid4())[:12])
    event_type: str
    project_id: str
    project_name: str = ""
    ref: str = "main"
    status: WorkflowStatus = WorkflowStatus.PENDING
    tasks: List[AgentTask] = []
    agents_involved: List[str] = []
    reasoning_chain: List[Dict[str, Any]] = []
    timeline_entries: List[TimelineEntry] = []
    trigger_payload: Dict[str, Any] = {}
    result: Dict[str, Any] = {}
    # Shared context bus — agents publish results here for downstream consumers
    shared_context: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def publish_context(self, agent_type: str, key: str, value: Any):
        """Publish data to the shared context bus for downstream agents."""
        if agent_type not in self.shared_context:
            self.shared_context[agent_type] = {}
        self.shared_context[agent_type][key] = value

    def consume_context(self, agent_type: str = None) -> Dict[str, Any]:
        """Consume shared context — optionally filter by source agent."""
        if agent_type:
            return self.shared_context.get(agent_type, {})
        return dict(self.shared_context)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None

    def add_timeline_entry(self, event: str, agent: str = None, detail: str = "", confidence: float = None):
        self.timeline_entries.append(TimelineEntry(
            timestamp=datetime.now(timezone.utc),
            event=event,
            agent=agent,
            detail=detail,
            confidence=confidence,
        ))

    def get_timeline(self) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "event": e.event,
                "agent": e.agent,
                "detail": e.detail,
                "confidence": e.confidence,
            }
            for e in self.timeline_entries
        ]

    def get_reasoning_nodes(self) -> List[Dict[str, Any]]:
        """Get nodes for reasoning tree visualization."""
        nodes = []
        for i, entry in enumerate(self.reasoning_chain):
            nodes.append({
                "id": f"node_{i}",
                "label": entry.get("step", f"Step {i}"),
                "type": entry.get("type", "reasoning"),
                "confidence": entry.get("confidence", 0.0),
                "risk": entry.get("risk", 0.0),
                "detail": entry.get("detail", ""),
                "agent": entry.get("agent", ""),
            })
        return nodes

    def get_reasoning_edges(self) -> List[Dict[str, Any]]:
        """Get edges for reasoning tree visualization."""
        edges = []
        for i in range(len(self.reasoning_chain) - 1):
            edges.append({
                "id": f"edge_{i}",
                "source": f"node_{i}",
                "target": f"node_{i+1}",
            })
        return edges

    def get_decision_path(self) -> List[str]:
        return [
            entry.get("decision", "")
            for entry in self.reasoning_chain
            if entry.get("decision")
        ]

    def get_confidence_scores(self) -> List[Dict[str, Any]]:
        return [
            {
                "step": entry.get("step", f"Step {i}"),
                "confidence": entry.get("confidence", 0.0),
            }
            for i, entry in enumerate(self.reasoning_chain)
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "event_type": self.event_type,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "status": self.status.value,
            "agents_involved": self.agents_involved,
            "task_count": len(self.tasks),
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def to_summary(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "event_type": self.event_type,
            "status": self.status.value,
            "agents": self.agents_involved,
            "created_at": self.created_at.isoformat(),
        }
