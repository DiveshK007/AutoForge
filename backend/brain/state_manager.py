"""
AutoForge State Manager — Workflow and system state tracking.
"""

from typing import Dict, List, Optional

from models.workflows import Workflow, WorkflowStatus


class StateManager:
    """
    Manages all workflow and system state.

    Tracks:
    - Active workflows
    - Completed workflows
    - Agent assignments
    - System health
    """

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._workflow_order: List[str] = []  # Maintains insertion order

    def register_workflow(self, workflow: Workflow):
        """Register a new workflow."""
        self._workflows[workflow.workflow_id] = workflow
        self._workflow_order.insert(0, workflow.workflow_id)

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def get_workflows(self, limit: int = 20, offset: int = 0) -> List[Workflow]:
        """Get workflows with pagination (most recent first)."""
        ids = self._workflow_order[offset:offset + limit]
        return [self._workflows[wid] for wid in ids if wid in self._workflows]

    def get_workflow_count(self) -> int:
        """Get total number of workflows."""
        return len(self._workflows)

    def get_active_workflows(self) -> List[Workflow]:
        """Get all currently active workflows."""
        active_statuses = {
            WorkflowStatus.PENDING,
            WorkflowStatus.ANALYZING,
            WorkflowStatus.PLANNING,
            WorkflowStatus.EXECUTING,
            WorkflowStatus.VALIDATING,
            WorkflowStatus.REFLECTING,
        }
        return [
            w for w in self._workflows.values()
            if w.status in active_statuses
        ]

    def get_completed_workflows(self, limit: int = 50) -> List[Workflow]:
        """Get completed workflows."""
        completed = [
            w for w in self._workflows.values()
            if w.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
        ]
        completed.sort(key=lambda w: w.completed_at or w.created_at, reverse=True)
        return completed[:limit]

    def get_system_stats(self) -> Dict:
        """Get system-wide statistics."""
        total = len(self._workflows)
        active = len(self.get_active_workflows())
        completed = sum(
            1 for w in self._workflows.values()
            if w.status == WorkflowStatus.COMPLETED
        )
        failed = sum(
            1 for w in self._workflows.values()
            if w.status == WorkflowStatus.FAILED
        )

        return {
            "total_workflows": total,
            "active_workflows": active,
            "completed_workflows": completed,
            "failed_workflows": failed,
            "success_rate": completed / max(completed + failed, 1),
        }
