"""
AutoForge Memory Store — Hybrid memory system for agent learning.

Implements:
- Short-term memory: Active workflow state
- Long-term memory: Failure patterns, fix outcomes
- Skill graph: Reusable remediation strategies
- Vector store: Repo embeddings for contextual reasoning
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict

from models.agents import AgentExperience
from models.workflows import Workflow


class MemoryStore:
    """
    Hybrid memory system for agent learning and recall.

    Memory layers:
    1. Short-term — Active task context (in-memory)
    2. Long-term — Historical patterns (persistent)
    3. Skill graph — Reusable strategies (derived)
    4. Vector memory — Semantic search (embeddings)
    """

    def __init__(self):
        # Short-term memory
        self._active_contexts: Dict[str, Any] = {}

        # Long-term memory
        self._experiences: List[AgentExperience] = []
        self._failure_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self._fix_outcomes: Dict[str, List[Dict]] = defaultdict(list)

        # Skill graph
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._skill_success_rates: Dict[str, float] = {}

        # Metrics
        self._recall_count = 0
        self._knowledge_reuse_count = 0

    async def initialize(self):
        """Initialize memory stores."""
        print("  🧠 Memory store initialized (in-memory mode)")

    async def shutdown(self):
        """Gracefully shutdown memory stores."""
        print(f"  🧠 Memory store shutdown. Experiences: {len(self._experiences)}, Skills: {len(self._skills)}")

    # ─── Experience Storage ───

    async def store_experience(self, experience: AgentExperience):
        """Store an agent experience in long-term memory."""
        self._experiences.append(experience)

        # Index by failure type
        self._failure_patterns[experience.failure_type].append({
            "agent": experience.agent_type,
            "action": experience.action_taken,
            "success": experience.success,
            "confidence": experience.confidence,
            "fix_time": experience.fix_time_seconds,
            "timestamp": experience.timestamp.isoformat(),
        })

        # Track fix outcomes
        outcome_key = f"{experience.agent_type}:{experience.action_taken}"
        self._fix_outcomes[outcome_key].append({
            "success": experience.success,
            "confidence": experience.confidence,
            "timestamp": experience.timestamp.isoformat(),
        })

        # Extract skill if successful
        if experience.success and experience.reusable_skill:
            await self._extract_skill(experience)

    async def store_workflow_experience(self, workflow: Workflow):
        """Store a complete workflow as an experience."""
        self._active_contexts[workflow.workflow_id] = {
            "event_type": workflow.event_type,
            "agents": workflow.agents_involved,
            "status": workflow.status.value,
            "duration": workflow.duration_seconds,
            "task_count": len(workflow.tasks),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        }

    # ─── Memory Recall ───

    async def recall(
        self, agent_type: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recall relevant prior knowledge for an agent task.

        Searches:
        1. Similar failure patterns
        2. Successful fix strategies
        3. Relevant skills
        """
        self._recall_count += 1
        result = {}

        event_type = context.get("event_type", "")
        error_logs = context.get("error_logs", "")

        # Find similar failures
        if event_type:
            similar = self._failure_patterns.get(event_type, [])
            if similar:
                successful = [s for s in similar if s["success"]]
                result["similar_fixes"] = successful[-5:]  # Last 5 successful
                result["failure_count"] = len(similar)
                result["success_rate"] = len(successful) / max(len(similar), 1)
                self._knowledge_reuse_count += 1

        # Find relevant skills
        relevant_skills = self._find_relevant_skills(agent_type, event_type)
        if relevant_skills:
            result["relevant_skills"] = relevant_skills

        # Get agent-specific fix history
        action = context.get("action", "")
        outcome_key = f"{agent_type}:{action}"
        if outcome_key in self._fix_outcomes:
            outcomes = self._fix_outcomes[outcome_key]
            result["past_outcomes"] = outcomes[-10:]
            result["historical_success_rate"] = (
                sum(1 for o in outcomes if o["success"]) / max(len(outcomes), 1)
            )

        return result

    # ─── Skill Management ───

    async def _extract_skill(self, experience: AgentExperience):
        """Extract a reusable skill from a successful experience."""
        skill_key = f"{experience.agent_type}:{experience.reusable_skill}"
        if skill_key not in self._skills:
            self._skills[skill_key] = {
                "name": experience.reusable_skill,
                "agent_type": experience.agent_type,
                "description": experience.context_summary,
                "usage_count": 0,
                "success_count": 0,
                "avg_confidence": 0.0,
                "created_at": experience.timestamp.isoformat(),
            }

        skill = self._skills[skill_key]
        skill["usage_count"] += 1
        if experience.success:
            skill["success_count"] += 1
        skill["avg_confidence"] = (
            (skill["avg_confidence"] * (skill["usage_count"] - 1) + experience.confidence)
            / skill["usage_count"]
        )

        # Update success rate
        self._skill_success_rates[skill_key] = (
            skill["success_count"] / skill["usage_count"]
        )

    def _find_relevant_skills(self, agent_type: str, event_type: str) -> List[Dict]:
        """Find skills relevant to an agent and event type."""
        relevant = []
        for key, skill in self._skills.items():
            if skill["agent_type"] == agent_type:
                relevant.append({
                    "name": skill["name"],
                    "success_rate": self._skill_success_rates.get(key, 0.0),
                    "usage_count": skill["usage_count"],
                    "confidence": skill["avg_confidence"],
                })
        return sorted(relevant, key=lambda s: s["success_rate"], reverse=True)[:5]

    # ─── Query Methods ───

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "total_experiences": len(self._experiences),
            "failure_pattern_types": len(self._failure_patterns),
            "total_skills": len(self._skills),
            "recall_count": self._recall_count,
            "knowledge_reuse_count": self._knowledge_reuse_count,
            "memory_utilization": (
                self._knowledge_reuse_count / max(self._recall_count, 1)
            ),
        }

    def get_skills(self) -> List[Dict[str, Any]]:
        """Get all learned skills."""
        return [
            {**skill, "success_rate": self._skill_success_rates.get(key, 0.0)}
            for key, skill in self._skills.items()
        ]

    def get_learning_curve(self) -> List[Dict[str, Any]]:
        """Get learning improvement data over time."""
        if not self._experiences:
            return []

        curve = []
        running_success = 0
        for i, exp in enumerate(self._experiences):
            if exp.success:
                running_success += 1
            curve.append({
                "index": i,
                "success_rate": running_success / (i + 1),
                "confidence": exp.confidence,
                "fix_time": exp.fix_time_seconds,
                "timestamp": exp.timestamp.isoformat(),
            })
        return curve
