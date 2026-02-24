"""
AutoForge Command Brain — Central Orchestrator.

The Command Brain is the AI Engineering Manager that:
- Ingests GitLab events
- Decomposes tasks
- Routes to specialized agents
- Tracks workflow state
- Resolves conflicts
- Aggregates outputs
- Triggers learning loops
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models.events import NormalizedEvent, EventType
from models.workflows import (
    Workflow,
    WorkflowStatus,
    AgentTask,
    TaskStatus,
    TaskPriority,
)
from brain.router import AgentRouter
from brain.state_manager import StateManager
from brain.task_decomposer import TaskDecomposer
from brain.conflict_resolver import ConflictResolver
from brain.policy_engine import PolicyEngine


class CommandBrain:
    """
    Central command brain — the AI Engineering Manager.

    Coordinates all agent activity, maintains system state,
    and ensures coherent multi-agent orchestration.
    """

    def __init__(self):
        self.state_manager = StateManager()
        self.router = AgentRouter()
        self.decomposer = TaskDecomposer()
        self.conflict_resolver = ConflictResolver()
        self.policy_engine = PolicyEngine()
        self.memory = None
        self.telemetry = None
        self._agents: Dict[str, Any] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize the agent workforce."""
        from agents.sre.agent import SREAgent
        from agents.security.agent import SecurityAgent
        from agents.qa.agent import QAAgent
        from agents.review.agent import ReviewAgent
        from agents.docs.agent import DocsAgent
        from agents.greenops.agent import GreenOpsAgent

        self._agents = {
            "sre": SREAgent(),
            "security": SecurityAgent(),
            "qa": QAAgent(),
            "review": ReviewAgent(),
            "docs": DocsAgent(),
            "greenops": GreenOpsAgent(),
        }

        print(f"  🤖 Initialized {len(self._agents)} agents: {list(self._agents.keys())}")

    def set_memory(self, memory):
        """Inject memory store dependency."""
        self.memory = memory
        for agent in self._agents.values():
            agent.set_memory(memory)

    def set_telemetry(self, telemetry):
        """Inject telemetry collector dependency."""
        self.telemetry = telemetry
        for agent in self._agents.values():
            agent.set_telemetry(telemetry)

    # ─── Event Ingestion ───

    async def ingest_event(self, event: NormalizedEvent) -> str:
        """
        Ingest a normalized event and create a workflow.

        Flow:
        1. Create workflow
        2. Decompose into tasks
        3. Check policies
        4. Route to agents
        5. Execute tasks
        6. Validate & reflect
        """
        # Create workflow
        workflow = Workflow(
            event_type=event.event_type.value,
            project_id=event.project_id,
            project_name=event.project_name,
            ref=event.ref,
            trigger_payload=event.payload,
        )
        workflow.add_timeline_entry("workflow_created", detail=f"Event: {event.event_type.value}")

        # Store workflow
        self.state_manager.register_workflow(workflow)

        # Log telemetry
        if self.telemetry:
            await self.telemetry.log_event("workflow_created", {
                "workflow_id": workflow.workflow_id,
                "event_type": event.event_type.value,
                "project_id": event.project_id,
            })

        # Process asynchronously
        asyncio.create_task(self._process_workflow(workflow, event))

        return workflow.workflow_id

    async def _process_workflow(self, workflow: Workflow, event: NormalizedEvent):
        """Process a workflow through the full agent pipeline."""
        try:
            # ─── Phase 1: Task Decomposition ───
            workflow.status = WorkflowStatus.ANALYZING
            workflow.add_timeline_entry("decomposition_started", detail="Analyzing event and creating tasks")

            tasks = self.decomposer.decompose(event)
            workflow.tasks = tasks

            # ─── Phase 2: Policy Check ───
            for task in tasks:
                allowed, reason = self.policy_engine.check_policy(task, workflow)
                if not allowed:
                    task.status = TaskStatus.SKIPPED
                    workflow.add_timeline_entry(
                        "task_skipped",
                        agent=task.agent_type,
                        detail=f"Policy blocked: {reason}",
                    )

            # ─── Phase 3: Conflict Resolution ───
            tasks = self.conflict_resolver.resolve(tasks)

            # ─── Phase 4: Execute Tasks ───
            workflow.status = WorkflowStatus.EXECUTING
            workflow.add_timeline_entry("execution_started", detail=f"Executing {len(tasks)} tasks")

            for task in tasks:
                if task.status == TaskStatus.SKIPPED:
                    continue

                agent = self._agents.get(task.agent_type)
                if not agent:
                    task.status = TaskStatus.FAILED
                    task.error = f"Agent {task.agent_type} not found"
                    continue

                workflow.agents_involved.append(task.agent_type)
                workflow.add_timeline_entry(
                    "task_assigned",
                    agent=task.agent_type,
                    detail=f"Action: {task.action}",
                )

                # Execute agent task
                try:
                    result = await agent.execute(task, workflow)
                    task.status = TaskStatus.COMPLETED
                    task.output_data = result.get("output", {})
                    task.reasoning = result.get("reasoning", {})
                    task.confidence = result.get("confidence", 0.0)
                    task.risk_score = result.get("risk_score", 0.0)
                    task.completed_at = datetime.now(timezone.utc)

                    # Add reasoning to workflow chain
                    workflow.reasoning_chain.append({
                        "step": f"{task.agent_type}_{task.action}",
                        "type": "agent_execution",
                        "agent": task.agent_type,
                        "decision": result.get("decision", ""),
                        "confidence": task.confidence,
                        "risk": task.risk_score,
                        "detail": result.get("summary", ""),
                    })

                    workflow.add_timeline_entry(
                        "task_completed",
                        agent=task.agent_type,
                        detail=result.get("summary", "Task completed"),
                        confidence=task.confidence,
                    )

                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now(timezone.utc)

                    workflow.add_timeline_entry(
                        "task_failed",
                        agent=task.agent_type,
                        detail=str(e),
                    )

                    # ─── Self-correction attempt ───
                    if task.agent_type == "sre" and self._should_retry(task):
                        workflow.add_timeline_entry(
                            "self_correction",
                            agent=task.agent_type,
                            detail="Attempting alternate strategy",
                        )
                        retry_result = await agent.retry_with_reflection(task, workflow, str(e))
                        if retry_result.get("success"):
                            task.status = TaskStatus.COMPLETED
                            task.output_data = retry_result.get("output", {})

            # ─── Phase 5: Validation ───
            workflow.status = WorkflowStatus.VALIDATING
            workflow.add_timeline_entry("validation_started", detail="Validating outcomes")

            # ─── Phase 6: Reflection ───
            workflow.status = WorkflowStatus.REFLECTING
            await self._reflect_on_workflow(workflow)

            # ─── Phase 7: Complete ───
            all_completed = all(
                t.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED) for t in workflow.tasks
            )
            workflow.status = WorkflowStatus.COMPLETED if all_completed else WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.add_timeline_entry(
                "workflow_completed",
                detail=f"Status: {workflow.status.value}, Duration: {workflow.duration_seconds:.1f}s",
            )

            # ─── Phase 8: Memory Encoding ───
            if self.memory:
                await self.memory.store_workflow_experience(workflow)

            # ─── Phase 9: Telemetry ───
            if self.telemetry:
                await self.telemetry.log_workflow_completed(workflow)

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.add_timeline_entry("workflow_error", detail=str(e))

    def _should_retry(self, task: AgentTask) -> bool:
        """Determine if a failed task should be retried."""
        from config import settings
        return task.status == TaskStatus.FAILED and settings.AGENT_MAX_RETRIES > 0

    async def _reflect_on_workflow(self, workflow: Workflow):
        """Perform system-level reflection on workflow outcomes."""
        successful_tasks = [t for t in workflow.tasks if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in workflow.tasks if t.status == TaskStatus.FAILED]

        workflow.reasoning_chain.append({
            "step": "system_reflection",
            "type": "reflection",
            "detail": f"Completed {len(successful_tasks)}/{len(workflow.tasks)} tasks",
            "confidence": len(successful_tasks) / max(len(workflow.tasks), 1),
            "risk": len(failed_tasks) / max(len(workflow.tasks), 1),
            "decision": "workflow_assessment",
        })

    # ─── Query Methods ───

    def get_agent_registry(self) -> Dict[str, Any]:
        return self._agents

    def get_agent(self, agent_id: str):
        return self._agents.get(agent_id)

    def get_workflows(self, limit: int = 20, offset: int = 0) -> List[Workflow]:
        return self.state_manager.get_workflows(limit=limit, offset=offset)

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self.state_manager.get_workflow(workflow_id)

    def get_workflow_count(self) -> int:
        return self.state_manager.get_workflow_count()

    async def cancel_workflow(self, workflow_id: str) -> bool:
        workflow = self.state_manager.get_workflow(workflow_id)
        if workflow and workflow.status not in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.add_timeline_entry("workflow_cancelled", detail="Cancelled by user")
            return True
        return False
