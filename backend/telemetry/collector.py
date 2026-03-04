"""
AutoForge Telemetry Collector — Metrics, observability, and intelligence tracking.

Tracks and stores:
- Success rate
- Fix time
- Confidence scores
- Reasoning depth
- Collaboration index
- Self-correction rate
- Carbon efficiency
- Learning curves
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from collections import defaultdict

from logging_config import get_logger
from models.agents import AgentAction
from models.workflows import Workflow, WorkflowStatus

log = get_logger("telemetry")


class TelemetryCollector:
    """
    Central telemetry collector for AutoForge system intelligence metrics.

    Feeds the dashboard with real-time and historical data.
    """

    def __init__(self):
        # Event log
        self._events: List[Dict[str, Any]] = []
        self._activity_feed: List[Dict[str, Any]] = []

        # Workflow metrics
        self._workflow_metrics: List[Dict[str, Any]] = []
        self._completed_workflows: int = 0
        self._failed_workflows: int = 0
        self._total_fix_time: float = 0.0

        # Agent metrics
        self._agent_actions: Dict[str, List[AgentAction]] = defaultdict(list)
        self._agent_metrics: Dict[str, Dict[str, Any]] = {}

        # Reasoning metrics
        self._reasoning_trees: List[Dict[str, Any]] = []
        self._reasoning_depths: List[int] = []

        # Collaboration metrics
        self._multi_agent_workflows: int = 0
        self._total_workflows: int = 0

        # Self-correction metrics
        self._self_corrections: int = 0
        self._failed_first_attempts: int = 0

        # Sustainability metrics
        self._total_energy_kwh: float = 0.0
        self._total_carbon_kg: float = 0.0
        self._optimizations_suggested: int = 0
        self._energy_saved_kwh: float = 0.0

        # Learning metrics
        self._confidence_history: List[float] = []
        self._success_history: List[bool] = []

    async def initialize(self):
        """Initialize telemetry system."""
        log.info("telemetry_initialized")

    async def shutdown(self):
        """Shutdown telemetry system."""
        log.info("telemetry_shutdown", events_logged=len(self._events))

    # ─── Event Logging ───

    async def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log a system event."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._events.append(event)

        # Add to activity feed
        self._activity_feed.insert(0, {
            "event": event_type,
            "detail": str(data.get("workflow_id", data.get("agent", "")))[:100],
            "timestamp": event["timestamp"],
        })

        # Cap activity feed size
        if len(self._activity_feed) > 200:
            self._activity_feed = self._activity_feed[:200]

        # Broadcast via WebSocket (best-effort)
        try:
            from api.websocket import broadcast_activity
            await broadcast_activity(event_type, str(data.get("workflow_id", data.get("agent", "")))[:100])
        except Exception:
            pass

    async def log_agent_action(self, action: AgentAction):
        """Log an agent action."""
        self._agent_actions[action.agent_type].append(action)

        # Update agent metrics
        if action.agent_type not in self._agent_metrics:
            self._agent_metrics[action.agent_type] = {
                "total_actions": 0,
                "successful_actions": 0,
                "total_confidence": 0.0,
                "total_duration_ms": 0,
            }

        metrics = self._agent_metrics[action.agent_type]
        metrics["total_actions"] += 1
        if action.success:
            metrics["successful_actions"] += 1
        metrics["total_confidence"] += action.confidence
        metrics["total_duration_ms"] += action.duration_ms

        # Track confidence history
        self._confidence_history.append(action.confidence)
        self._success_history.append(action.success)

        await self.log_event("agent_action", {
            "agent": action.agent_type,
            "action": action.action_type,
            "success": action.success,
            "confidence": action.confidence,
        })

    async def log_workflow_completed(self, workflow: Workflow):
        """Log a completed workflow."""
        self._total_workflows += 1

        if workflow.status == WorkflowStatus.COMPLETED:
            self._completed_workflows += 1
        else:
            self._failed_workflows += 1

        if workflow.duration_seconds:
            self._total_fix_time += workflow.duration_seconds

        # Multi-agent tracking
        if len(workflow.agents_involved) > 1:
            self._multi_agent_workflows += 1

        # Check for self-corrections
        for task in workflow.tasks:
            if task.output_data.get("self_corrected"):
                self._self_corrections += 1

        # Track sustainability metrics
        for task in workflow.tasks:
            if task.agent_type == "greenops":
                energy = task.output_data.get("energy_report", {})
                self._total_energy_kwh += energy.get("energy_kwh", 0)
                self._total_carbon_kg += energy.get("carbon_kg", 0)
                self._optimizations_suggested += len(
                    task.output_data.get("optimizations", [])
                )

        # Store workflow metric point
        self._workflow_metrics.append({
            "workflow_id": workflow.workflow_id,
            "status": workflow.status.value,
            "duration": workflow.duration_seconds,
            "agents": workflow.agents_involved,
            "task_count": len(workflow.tasks),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Store reasoning trees
        if workflow.reasoning_chain:
            self._reasoning_trees.append({
                "workflow_id": workflow.workflow_id,
                "chain": workflow.reasoning_chain,
                "nodes": workflow.get_reasoning_nodes(),
                "edges": workflow.get_reasoning_edges(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self._reasoning_depths.append(len(workflow.reasoning_chain))

    # ─── Metric Queries ───

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system-wide metrics."""
        total = self._completed_workflows + self._failed_workflows

        # Agent-level metrics
        agent_metrics = {}
        for agent_type, metrics in self._agent_metrics.items():
            total_actions = metrics["total_actions"]
            agent_metrics[agent_type] = {
                "total_actions": total_actions,
                "success_rate": metrics["successful_actions"] / max(total_actions, 1),
                "avg_confidence": metrics["total_confidence"] / max(total_actions, 1),
                "avg_duration_ms": metrics["total_duration_ms"] / max(total_actions, 1),
            }

        return {
            "success_rate": self._completed_workflows / max(total, 1),
            "avg_fix_time": self._total_fix_time / max(self._completed_workflows, 1),
            "total_workflows": self._total_workflows,
            "active_workflows": 0,  # Would come from state manager
            "total_fixes": self._completed_workflows,
            "avg_confidence": (
                sum(self._confidence_history) / max(len(self._confidence_history), 1)
            ),
            "self_correction_rate": (
                self._self_corrections / max(self._failed_first_attempts or 1, 1)
            ),
            "collaboration_index": (
                self._multi_agent_workflows / max(self._total_workflows, 1)
            ),
            "memory_utilization": 0.0,  # Would come from memory store
            "knowledge_reuse": 0,
            "policy_trend": self._get_confidence_trend(),
            "reasoning_depth": (
                sum(self._reasoning_depths) / max(len(self._reasoning_depths), 1)
            ),
            "carbon_score": self._calculate_carbon_score(),
            "energy_saved": self._energy_saved_kwh,
            "pipeline_efficiency": self._calculate_pipeline_efficiency(),
            "optimizations": self._optimizations_suggested,
            "agent_metrics": agent_metrics,
            "learning_score": self._calculate_learning_score(),
        }

    async def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics."""
        return self._workflow_metrics[-100:]  # Last 100 data points

    async def get_recent_reasoning_trees(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent reasoning trees."""
        return self._reasoning_trees[-limit:]

    async def get_learning_curve(self) -> List[Dict[str, Any]]:
        """Get learning curve data."""
        if not self._success_history:
            return []

        curve = []
        running_success = 0
        for i, success in enumerate(self._success_history):
            if success:
                running_success += 1
            curve.append({
                "index": i,
                "success_rate": running_success / (i + 1),
                "confidence": self._confidence_history[i] if i < len(self._confidence_history) else 0.0,
            })
        return curve

    async def get_activity_feed(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity feed."""
        return self._activity_feed[:limit]

    async def calculate_meta_intelligence(self) -> float:
        """
        Calculate the Meta Intelligence Score (MIS).

        Formula: (Accuracy×0.3 + Learning×0.25 + Reflection×0.2 + Collaboration×0.15 + Sustainability×0.1)
        Weighted to emphasize the competition's judging criteria.
        """
        total = self._completed_workflows + self._failed_workflows
        accuracy = self._completed_workflows / max(total, 1)
        learning = self._calculate_learning_score()
        reflection = min(self._self_corrections / max(self._failed_first_attempts or 1, 1), 1.0)
        collaboration = self._multi_agent_workflows / max(self._total_workflows, 1)
        sustainability = self._calculate_carbon_score() / 100.0  # Normalize to 0-1

        meta_score = (
            accuracy * 0.30
            + learning * 0.25
            + reflection * 0.20
            + collaboration * 0.15
            + sustainability * 0.10
        )
        return round(meta_score, 4)

    # ─── Internal Calculations ───

    def _get_confidence_trend(self) -> List[float]:
        """Get confidence scores over time."""
        if not self._confidence_history:
            return []
        # Return last 20 data points
        return self._confidence_history[-20:]

    def _calculate_carbon_score(self) -> float:
        """Calculate carbon efficiency score (0-100)."""
        if self._total_energy_kwh == 0:
            return 100.0
        # Score based on energy per workflow
        energy_per_workflow = self._total_energy_kwh / max(self._total_workflows, 1)
        # Lower energy = higher score
        score = max(0, 100 - (energy_per_workflow * 10000))
        return round(score, 2)

    def _calculate_pipeline_efficiency(self) -> float:
        """Calculate pipeline efficiency percentage."""
        if self._total_workflows == 0:
            return 100.0
        return round(
            (self._completed_workflows / max(self._total_workflows, 1)) * 100, 2
        )

    def _calculate_learning_score(self) -> float:
        """Calculate learning improvement score."""
        if len(self._success_history) < 2:
            return 0.0

        # Compare first half vs second half success rates
        mid = len(self._success_history) // 2
        first_half = sum(1 for s in self._success_history[:mid] if s) / max(mid, 1)
        second_half = sum(1 for s in self._success_history[mid:] if s) / max(
            len(self._success_history) - mid, 1
        )

        improvement = second_half - first_half
        return round(max(0, min(1, 0.5 + improvement)), 4)
