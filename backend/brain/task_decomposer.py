"""
AutoForge Task Decomposer — Breaks events into agent-assignable tasks with DAG dependencies.
"""

from typing import Dict, List

from models.events import NormalizedEvent, EventType
from models.workflows import AgentTask, TaskPriority
from brain.router import AgentRouter


# ─── Dependency Graph: which agent types must complete before others can start ──
AGENT_DEPENDENCY_MAP: Dict[str, Dict[str, List[str]]] = {
    EventType.PIPELINE_FAILURE.value: {
        "sre": [],                        # SRE runs first — diagnoses
        "security": ["sre"],              # Security validates SRE's fix
        "qa": ["sre"],                    # QA generates tests for fix
        "docs": ["sre"],                  # Docs updates changelog after fix
        "greenops": [],                   # GreenOps runs independently
    },
    EventType.SECURITY_ALERT.value: {
        "security": [],                   # Security leads
        "sre": ["security"],              # SRE assesses impact after analysis
        "qa": ["security"],               # QA validates patch
    },
    EventType.MERGE_REQUEST_OPENED.value: {
        "review": [],                     # Review runs first
        "security": [],                   # Security scans independently
        "qa": ["review"],                 # QA acts on review findings
    },
    EventType.MERGE_REQUEST_MERGED.value: {
        "docs": [],
        "greenops": [],
    },
}


class TaskDecomposer:
    """
    Decomposes normalized events into structured agent tasks with DAG dependencies.

    Implements the cognitive pipeline:
    Event → Context Analysis → Task Generation → Dependency Wiring → Priority Assignment
    """

    def __init__(self):
        self.router = AgentRouter()

    def decompose(self, event: NormalizedEvent) -> List[AgentTask]:
        """Decompose an event into a DAG of agent tasks."""
        agents = self.router.get_agents_for_event(event.event_type.value)
        tasks = []
        task_id_map: Dict[str, str] = {}  # agent_type → task_id

        # First pass: create all tasks and record their IDs
        for agent_type in agents:
            action = self.router.get_action_for_agent(event.event_type.value, agent_type)
            priority = self._determine_priority(event, agent_type)

            task = AgentTask(
                workflow_id="",  # Will be set by orchestrator
                agent_type=agent_type,
                action=action,
                priority=priority,
                input_data=self._build_task_input(event, agent_type),
            )
            tasks.append(task)
            task_id_map[agent_type] = task.task_id

        # Second pass: wire up dependencies from the DAG map
        dep_map = AGENT_DEPENDENCY_MAP.get(event.event_type.value, {})
        for task in tasks:
            agent_deps = dep_map.get(task.agent_type, [])
            task.dependencies = [
                task_id_map[dep_agent]
                for dep_agent in agent_deps
                if dep_agent in task_id_map
            ]

        # Sort: tasks with no dependencies first, then by priority
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        tasks.sort(key=lambda t: (len(t.dependencies), priority_order.get(t.priority, 99)))

        return tasks

    def _determine_priority(self, event: NormalizedEvent, agent_type: str) -> TaskPriority:
        """Determine task priority based on event type and agent role."""
        if event.event_type == EventType.PIPELINE_FAILURE:
            if agent_type == "sre":
                return TaskPriority.CRITICAL
            elif agent_type == "security":
                return TaskPriority.HIGH
            elif agent_type == "qa":
                return TaskPriority.HIGH
            else:
                return TaskPriority.MEDIUM

        elif event.event_type == EventType.SECURITY_ALERT:
            if agent_type == "security":
                return TaskPriority.CRITICAL
            return TaskPriority.HIGH

        elif event.event_type == EventType.MERGE_REQUEST_OPENED:
            if agent_type == "review":
                return TaskPriority.HIGH
            return TaskPriority.MEDIUM

        return TaskPriority.MEDIUM

    def _build_task_input(self, event: NormalizedEvent, agent_type: str) -> dict:
        """Build agent-specific input data from the event."""
        base_input = {
            "event_type": event.event_type.value,
            "project_id": event.project_id,
            "project_name": event.project_name,
            "ref": event.ref,
            "timestamp": event.timestamp.isoformat(),
        }

        # Add event-specific data
        if event.event_type == EventType.PIPELINE_FAILURE:
            base_input.update({
                "pipeline_id": event.payload.get("pipeline_id"),
                "pipeline_url": event.payload.get("pipeline_url"),
                "failed_jobs": event.payload.get("failed_jobs", []),
                "error_logs": event.payload.get("error_logs", ""),
                "commit_sha": event.payload.get("commit_sha"),
                "commit_message": event.payload.get("commit_message"),
            })

        elif event.event_type in (EventType.SECURITY_ALERT, EventType.DEPENDENCY_ALERT):
            base_input.update({
                "vulnerability_id": event.payload.get("vulnerability_id"),
                "severity": event.payload.get("severity"),
                "package": event.payload.get("package"),
                "current_version": event.payload.get("current_version"),
                "fixed_version": event.payload.get("fixed_version"),
                "cve_id": event.payload.get("cve_id"),
            })

        elif event.event_type in (EventType.MERGE_REQUEST_OPENED, EventType.MERGE_REQUEST_UPDATED):
            base_input.update({
                "mr_id": event.payload.get("mr_id"),
                "mr_title": event.payload.get("mr_title"),
                "mr_description": event.payload.get("mr_description"),
                "source_branch": event.payload.get("source_branch"),
                "target_branch": event.payload.get("target_branch"),
                "diff": event.payload.get("diff"),
                "changed_files": event.payload.get("changed_files", []),
            })

        return base_input
