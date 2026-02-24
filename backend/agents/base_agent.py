"""
AutoForge Base Agent — Universal agent architecture.

Every agent follows the cognition pipeline:
Perception → Reasoning → Planning → Tool Execution → Reflection → Memory Encoding
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models.workflows import AgentTask, Workflow
from models.agents import (
    AgentAction,
    AgentExperience,
    ReasoningTree,
    ReasoningNode,
    Hypothesis,
)


class BaseAgent(ABC):
    """
    Base class for all AutoForge agents.

    Implements the universal cognition pipeline:
    1. Perception — Read and understand context
    2. Reasoning — Generate and evaluate hypotheses
    3. Planning — Select optimal action strategy
    4. Execution — Use tools to take action
    5. Reflection — Evaluate outcomes
    6. Memory — Store experiences for learning
    """

    def __init__(self, agent_type: str, capabilities: List[str]):
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.status = "idle"
        self.memory = None
        self.telemetry = None

        # Agent state
        self._active_tasks: List[str] = []
        self._action_history: List[AgentAction] = []
        self._reasoning_trees: List[ReasoningTree] = []
        self._hypotheses: List[Hypothesis] = []
        self._stats = {
            "total_completed": 0,
            "total_failed": 0,
            "total_confidence": 0.0,
            "active_tasks": 0,
            "last_active": None,
        }

    def set_memory(self, memory):
        self.memory = memory

    def set_telemetry(self, telemetry):
        self.telemetry = telemetry

    # ─── Main Execution Pipeline ───

    async def execute(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """
        Execute the full cognition pipeline for a task.

        Returns a result dict with:
        - output: execution output data
        - reasoning: structured reasoning chain
        - confidence: confidence score (0-1)
        - risk_score: risk assessment (0-1)
        - decision: the chosen action
        - summary: human-readable summary
        """
        start_time = time.time()
        self.status = "active"
        self._stats["active_tasks"] += 1
        self._stats["last_active"] = datetime.now(timezone.utc).isoformat()

        try:
            # ─── 1. Perception ───
            context = await self.perceive(task, workflow)

            # ─── 2. Check Memory ───
            prior_knowledge = await self._recall_memory(task)

            # ─── 3. Reasoning ───
            reasoning_result = await self.reason(context, prior_knowledge)

            # ─── 4. Planning ───
            plan = await self.plan(reasoning_result)

            # ─── 5. Tool Execution ───
            execution_result = await self.act(plan, task, workflow)

            # ─── 6. Reflection ───
            reflection = await self.reflect(execution_result, plan)

            # ─── 7. Memory Encoding ───
            await self._encode_memory(task, execution_result, reflection)

            # ─── Build Result ───
            elapsed_ms = int((time.time() - start_time) * 1000)

            action = AgentAction(
                action_id=str(uuid4())[:12],
                agent_type=self.agent_type,
                action_type=task.action,
                description=execution_result.get("summary", ""),
                confidence=reasoning_result.get("confidence", 0.0),
                risk_score=reasoning_result.get("risk_score", 0.0),
                success=True,
                duration_ms=elapsed_ms,
                tools_used=execution_result.get("tools_used", []),
            )
            self._action_history.append(action)

            self._stats["total_completed"] += 1
            self._stats["total_confidence"] += reasoning_result.get("confidence", 0.0)

            if self.telemetry:
                await self.telemetry.log_agent_action(action)

            return {
                "output": execution_result.get("output", {}),
                "reasoning": reasoning_result,
                "confidence": reasoning_result.get("confidence", 0.0),
                "risk_score": reasoning_result.get("risk_score", 0.0),
                "decision": plan.get("chosen_action", ""),
                "summary": execution_result.get("summary", ""),
                "reflection": reflection,
                "tools_used": execution_result.get("tools_used", []),
                "duration_ms": elapsed_ms,
            }

        except Exception as e:
            self._stats["total_failed"] += 1
            raise
        finally:
            self._stats["active_tasks"] -= 1
            if self._stats["active_tasks"] == 0:
                self.status = "idle"

    async def retry_with_reflection(
        self, task: AgentTask, workflow: Workflow, error: str
    ) -> Dict[str, Any]:
        """Retry a failed task with reflection on the failure."""
        # Build reflection context
        reflection_context = {
            "previous_error": error,
            "original_task": task.action,
            "instruction": "Previous attempt failed. Analyze the failure and try an alternate strategy.",
        }
        task.input_data["retry_context"] = reflection_context

        try:
            result = await self.execute(task, workflow)
            result["self_corrected"] = True
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Abstract Cognition Methods ───

    @abstractmethod
    async def perceive(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """
        Perception layer — read and understand context.
        Returns structured context for reasoning.
        """
        pass

    @abstractmethod
    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reasoning layer — generate hypotheses, evaluate alternatives.
        Returns reasoning result with confidence and risk scores.
        """
        pass

    @abstractmethod
    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        Planning layer — select optimal action strategy.
        Returns an action plan.
        """
        pass

    @abstractmethod
    async def act(self, plan: Dict[str, Any], task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """
        Execution layer — use tools to take action.
        Returns execution result.
        """
        pass

    @abstractmethod
    async def reflect(self, result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reflection layer — evaluate outcomes and self-critique.
        Returns reflection summary.
        """
        pass

    # ─── Memory Methods ───

    async def _recall_memory(self, task: AgentTask) -> Dict[str, Any]:
        """Recall relevant prior knowledge from memory."""
        if not self.memory:
            return {}

        return await self.memory.recall(
            agent_type=self.agent_type,
            context={
                "action": task.action,
                "event_type": task.input_data.get("event_type"),
                "error_logs": task.input_data.get("error_logs", ""),
            },
        )

    async def _encode_memory(
        self, task: AgentTask, result: Dict[str, Any], reflection: Dict[str, Any]
    ):
        """Encode the experience into memory."""
        if not self.memory:
            return

        experience = AgentExperience(
            experience_id=str(uuid4())[:12],
            agent_type=self.agent_type,
            failure_type=task.input_data.get("event_type", "unknown"),
            context_summary=result.get("summary", ""),
            action_taken=task.action,
            outcome=reflection.get("outcome", ""),
            success=reflection.get("success", False),
            confidence=result.get("confidence", 0.0),
            fix_time_seconds=result.get("duration_ms", 0) / 1000,
            reusable_skill=reflection.get("extracted_skill"),
        )

        await self.memory.store_experience(experience)

    # ─── Query Methods ───

    def get_stats(self) -> Dict[str, Any]:
        total = self._stats["total_completed"] + self._stats["total_failed"]
        return {
            "active_tasks": self._stats["active_tasks"],
            "total_completed": self._stats["total_completed"],
            "total_failed": self._stats["total_failed"],
            "success_rate": self._stats["total_completed"] / max(total, 1),
            "avg_confidence": (
                self._stats["total_confidence"] / max(self._stats["total_completed"], 1)
            ),
            "last_active": self._stats["last_active"],
        }

    def get_active_reasoning(self) -> Optional[Dict[str, Any]]:
        if self._reasoning_trees:
            return self._reasoning_trees[-1].to_visualization()
        return None

    def get_reasoning_tree(self) -> Optional[Dict[str, Any]]:
        if self._reasoning_trees:
            return self._reasoning_trees[-1].to_visualization()
        return None

    def get_hypotheses(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": h.hypothesis_id,
                "description": h.description,
                "probability": h.probability,
                "evidence": h.evidence,
                "confidence": h.confidence,
            }
            for h in self._hypotheses[-10:]
        ]

    def get_decision_path(self) -> List[str]:
        return [a.description for a in self._action_history[-5:]]

    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [
            {
                "action_id": a.action_id,
                "type": a.action_type,
                "description": a.description,
                "confidence": a.confidence,
                "success": a.success,
                "duration_ms": a.duration_ms,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in self._action_history[-limit:]
        ]
