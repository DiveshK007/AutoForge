"""
AutoForge Command Brain — Central Orchestrator.

The Command Brain is the AI Engineering Manager that:
- Ingests GitLab events
- Decomposes tasks into a DAG
- Routes to specialized agents with dependency ordering
- Manages shared context bus between agents
- Tracks workflow state
- Resolves conflicts
- Aggregates outputs
- Triggers learning loops
- Supports DEMO_MODE for deterministic presentations
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from config import settings
from logging_config import get_logger
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

log = get_logger("brain")


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

        mode = "DEMO" if settings.DEMO_MODE else "LIVE"
        log.info("agents_initialized", count=len(self._agents), agents=list(self._agents.keys()), mode=mode)

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
        2. Decompose into DAG of tasks
        3. Check policies
        4. Execute in dependency order (sharing context)
        5. Validate & reflect
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

        # Broadcast new workflow via WebSocket
        try:
            from api.websocket import broadcast_workflow_update
            await broadcast_workflow_update(workflow.workflow_id, "created", {
                "event_type": event.event_type.value,
                "project_id": event.project_id,
            })
        except Exception:
            pass  # WebSocket is best-effort

        return workflow.workflow_id

    async def _process_workflow(self, workflow: Workflow, event: NormalizedEvent):
        """Process a workflow through the full agent pipeline with DAG execution."""
        try:
            # ─── Phase 1: Task Decomposition (with DAG) ───
            workflow.status = WorkflowStatus.ANALYZING
            workflow.add_timeline_entry("decomposition_started", detail="Analyzing event and creating task DAG")

            tasks = self.decomposer.decompose(event)
            workflow.tasks = tasks

            # Build task lookup for dependency resolution
            task_map: Dict[str, AgentTask] = {t.task_id: t for t in tasks}
            dep_info = ", ".join(
                f"{t.agent_type}(deps={[task_map[d].agent_type for d in t.dependencies if d in task_map]})"
                for t in tasks
            )
            workflow.add_timeline_entry(
                "dag_constructed",
                detail=f"Task DAG: {dep_info}",
            )

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

            # ─── Phase 4: DAG-Ordered Execution with Shared Context ───
            workflow.status = WorkflowStatus.EXECUTING
            active_count = sum(1 for t in tasks if t.status != TaskStatus.SKIPPED)
            workflow.add_timeline_entry("execution_started", detail=f"Executing {active_count} tasks in DAG order")

            completed_task_ids: Set[str] = set()

            # Execute in waves: tasks whose dependencies are all satisfied
            max_waves = 10  # safety limit
            for wave in range(max_waves):
                # Find tasks ready to run (all deps satisfied, not yet started)
                ready = [
                    t for t in tasks
                    if t.status == TaskStatus.QUEUED
                    and all(d in completed_task_ids for d in t.dependencies)
                ]

                if not ready:
                    break  # No more tasks to run

                workflow.add_timeline_entry(
                    "execution_wave",
                    detail=f"Wave {wave + 1}: executing {[t.agent_type for t in ready]}",
                )

                # Execute ready tasks (could parallelize with asyncio.gather for independent ones)
                for task in ready:
                    agent = self._agents.get(task.agent_type)
                    if not agent:
                        task.status = TaskStatus.FAILED
                        task.error = f"Agent {task.agent_type} not found"
                        completed_task_ids.add(task.task_id)
                        continue

                    # Inject shared context from upstream agents into task input
                    if workflow.shared_context:
                        task.input_data["_shared_context"] = workflow.consume_context()

                    if task.agent_type not in workflow.agents_involved:
                        workflow.agents_involved.append(task.agent_type)

                    workflow.add_timeline_entry(
                        "task_assigned",
                        agent=task.agent_type,
                        detail=f"Action: {task.action}" + (f" (depends on {[task_map[d].agent_type for d in task.dependencies if d in task_map]})" if task.dependencies else ""),
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

                        # Publish results to shared context bus
                        workflow.publish_context(task.agent_type, "result", result)
                        workflow.publish_context(task.agent_type, "confidence", task.confidence)
                        workflow.publish_context(task.agent_type, "decision", result.get("decision", ""))
                        workflow.publish_context(task.agent_type, "summary", result.get("summary", ""))

                        # Add reasoning to workflow chain
                        workflow.reasoning_chain.append({
                            "step": f"{task.agent_type}_{task.action}",
                            "type": "agent_execution",
                            "agent": task.agent_type,
                            "decision": result.get("decision", ""),
                            "confidence": task.confidence,
                            "risk": task.risk_score,
                            "detail": result.get("summary", ""),
                            "wave": wave + 1,
                            "dependencies": task.dependencies,
                        })

                        workflow.add_timeline_entry(
                            "task_completed",
                            agent=task.agent_type,
                            detail=result.get("summary", "Task completed"),
                            confidence=task.confidence,
                        )

                        # Broadcast agent completion via WebSocket
                        try:
                            from api.websocket import broadcast_agent_action
                            await broadcast_agent_action(
                                task.agent_type, task.action,
                                "completed", task.confidence,
                            )
                        except Exception:
                            pass

                    except Exception as e:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        task.completed_at = datetime.now(timezone.utc)

                        workflow.add_timeline_entry(
                            "task_failed",
                            agent=task.agent_type,
                            detail=str(e),
                        )

                        # ─── Self-correction: retry → alternate fix → escalate ───
                        retried = await self._retry_with_escalation(agent, task, workflow)
                        if retried:
                            # Publish corrected results to shared context
                            workflow.publish_context(task.agent_type, "self_corrected", True)
                            workflow.publish_context(task.agent_type, "confidence", task.confidence)

                    completed_task_ids.add(task.task_id)

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
                detail=f"Status: {workflow.status.value}, Duration: {workflow.duration_seconds:.1f}s, Agents: {workflow.agents_involved}",
            )

            # Broadcast workflow completion via WebSocket
            try:
                from api.websocket import broadcast_workflow_update
                await broadcast_workflow_update(
                    workflow.workflow_id, workflow.status.value,
                    {"duration": workflow.duration_seconds, "agents": workflow.agents_involved},
                )
            except Exception:
                pass

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

    async def _retry_with_escalation(
        self, agent, task: AgentTask, workflow: Workflow
    ) -> bool:
        """
        Retry strategy with escalation: retry → alternate fix → manual review.
        Records real retry history for dashboard visualization.
        Returns True if self-correction succeeded.
        """
        max_retries = settings.AGENT_MAX_RETRIES
        if not self._should_retry(task) or max_retries < 1:
            return False

        # Initialize retry history on workflow if not present
        if not hasattr(workflow, '_retry_history'):
            workflow._retry_history = []

        for attempt in range(1, max_retries + 1):
            strategy = f"Alternate strategy attempt {attempt}/{max_retries}"
            workflow.add_timeline_entry(
                "self_correction",
                agent=task.agent_type,
                detail=f"Retry attempt {attempt}/{max_retries} — alternate strategy",
            )

            import time
            start_ms = time.monotonic()

            try:
                retry_result = await agent.retry_with_reflection(task, workflow, task.error or "")
                duration_ms = int((time.monotonic() - start_ms) * 1000)

                if retry_result.get("success"):
                    task.status = TaskStatus.COMPLETED
                    task.output_data = retry_result.get("output", {})
                    task.output_data["self_corrected"] = True
                    task.confidence = retry_result.get("confidence", 0.0)
                    task.completed_at = datetime.now(timezone.utc)

                    # Record successful retry
                    workflow._retry_history.append({
                        "attempt": attempt,
                        "maxAttempts": max_retries,
                        "agent": task.agent_type,
                        "strategy": retry_result.get("strategy", strategy),
                        "outcome": "success",
                        "confidence": task.confidence,
                        "duration_ms": duration_ms,
                    })

                    workflow.add_timeline_entry(
                        "self_correction_success",
                        agent=task.agent_type,
                        detail=f"Self-corrected on attempt {attempt}",
                        confidence=task.confidence,
                    )
                    return True
                else:
                    # Record failed retry
                    workflow._retry_history.append({
                        "attempt": attempt,
                        "maxAttempts": max_retries,
                        "agent": task.agent_type,
                        "strategy": retry_result.get("strategy", strategy),
                        "outcome": "failure",
                        "confidence": retry_result.get("confidence", 0.0),
                        "duration_ms": duration_ms,
                    })
            except Exception as exc:
                duration_ms = int((time.monotonic() - start_ms) * 1000)
                workflow._retry_history.append({
                    "attempt": attempt,
                    "maxAttempts": max_retries,
                    "agent": task.agent_type,
                    "strategy": strategy,
                    "outcome": "failure",
                    "confidence": 0.0,
                    "duration_ms": duration_ms,
                })

        # Escalation: mark for manual review
        workflow.add_timeline_entry(
            "escalation",
            agent=task.agent_type,
            detail=f"Exhausted {max_retries} retries — escalating to manual review",
        )
        return False

    def _should_retry(self, task: AgentTask) -> bool:
        """Determine if a failed task should be retried."""
        return task.status == TaskStatus.FAILED and settings.AGENT_MAX_RETRIES > 0

    async def _reflect_on_workflow(self, workflow: Workflow):
        """Perform system-level reflection on workflow outcomes."""
        successful_tasks = [t for t in workflow.tasks if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in workflow.tasks if t.status == TaskStatus.FAILED]
        self_corrected = sum(1 for t in workflow.tasks if t.output_data.get("self_corrected"))

        reflection = {
            "step": "system_reflection",
            "type": "reflection",
            "detail": f"Completed {len(successful_tasks)}/{len(workflow.tasks)} tasks ({self_corrected} self-corrected)",
            "confidence": len(successful_tasks) / max(len(workflow.tasks), 1),
            "risk": len(failed_tasks) / max(len(workflow.tasks), 1),
            "decision": "workflow_assessment",
            "collaboration_index": len(set(workflow.agents_involved)) / max(len(self._agents), 1),
            "shared_context_keys": list(workflow.shared_context.keys()),
        }
        workflow.reasoning_chain.append(reflection)

        # Persist reflection insights to memory
        if self.memory and successful_tasks:
            for task in successful_tasks:
                reflection_data = task.reasoning.get("reflection", {})
                skill = reflection_data.get("extracted_skill") if isinstance(reflection_data, dict) else None
                if skill:
                    from models.agents import AgentExperience
                    exp = AgentExperience(
                        experience_id=f"refl_{task.task_id}",
                        agent_type=task.agent_type,
                        failure_type=workflow.event_type,
                        context_summary=task.output_data.get("summary", ""),
                        action_taken=task.action,
                        outcome="success",
                        success=True,
                        confidence=task.confidence,
                        fix_time_seconds=(
                            (task.completed_at - task.created_at).total_seconds()
                            if task.completed_at else 0
                        ),
                        reusable_skill=skill,
                    )
                    await self.memory.store_experience(exp)

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

    def get_retry_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get retry history for a workflow (real data from _retry_with_escalation)."""
        workflow = self.state_manager.get_workflow(workflow_id)
        if not workflow:
            return []
        return getattr(workflow, '_retry_history', [])

    def get_agent_communication(self, workflow_id: str) -> Dict[str, Any]:
        """Get agent-to-agent communication data from the shared context bus."""
        workflow = self.state_manager.get_workflow(workflow_id)
        if not workflow:
            return {"agents": [], "links": [], "context": {}}

        # Build communication graph from shared context
        agents = list(set(workflow.agents_involved))
        links = []
        context = {}

        for agent_type, data in workflow.shared_context.items():
            if isinstance(data, dict):
                context[agent_type] = data
                # Build links: each consuming agent that depends on this agent's output
                for task in workflow.tasks:
                    if task.agent_type != agent_type:
                        # Check if this task consumed context from agent_type
                        shared_in_input = task.input_data.get("_shared_context", {})
                        if agent_type in str(shared_in_input) or any(
                            d_task.agent_type == agent_type
                            for d_task in workflow.tasks
                            if d_task.task_id in task.dependencies
                        ):
                            # Determine data type exchanged
                            data_keys = list(data.keys()) if isinstance(data, dict) else []
                            data_type = data_keys[0] if data_keys else "context"
                            volume = min(1.0, len(data_keys) / 5.0) if data_keys else 0.3
                            links.append({
                                "from": agent_type,
                                "to": task.agent_type,
                                "dataType": data_type,
                                "volume": round(volume, 2),
                            })

        return {
            "agents": agents,
            "links": links,
            "context": context,
        }
