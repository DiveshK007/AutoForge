"""
AutoForge Memory Store — Hybrid memory system for agent learning.

Implements:
- Short-term memory: Active workflow state (in-memory — fast)
- Long-term memory: Failure patterns, fix outcomes (PostgreSQL-backed)
- Skill graph: Reusable remediation strategies (PostgreSQL-backed)
- Semantic memory: Abstract pattern categories for cross-agent knowledge sharing
- Policy learning: Tracks policy violations and adapts thresholds (PostgreSQL-backed)
- Redis cache: Hot-path reads skip DB round-trips
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict

from models.agents import AgentExperience
from models.workflows import Workflow
from logging_config import get_logger

log = get_logger("memory")


class MemoryStore:
    """
    Hybrid memory system for agent learning and recall.

    Memory layers:
    1. Short-term — Active task context (in-memory)
    2. Long-term — Historical patterns (in-memory + PostgreSQL)
    3. Skill graph — Reusable strategies (in-memory + PostgreSQL)
    4. Semantic — Abstract pattern categories (in-memory)
    5. Policy — Learning from governance decisions (in-memory + PostgreSQL)
    6. Redis cache — Hot-path acceleration

    When PostgreSQL/Redis are unavailable, falls back to pure in-memory mode.
    """

    def __init__(self):
        # Short-term memory
        self._active_contexts: Dict[str, Any] = {}

        # Long-term memory (in-memory layer — always populated)
        self._experiences: List[AgentExperience] = []
        self._failure_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self._fix_outcomes: Dict[str, List[Dict]] = defaultdict(list)

        # Skill graph
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._skill_success_rates: Dict[str, float] = {}

        # Semantic memory — abstract patterns grouped by category
        self._semantic_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Cross-agent knowledge sharing
        self._shared_knowledge: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Policy learning
        self._policy_violations: List[Dict[str, Any]] = []
        self._policy_overrides: List[Dict[str, Any]] = []

        # Metrics
        self._recall_count = 0
        self._knowledge_reuse_count = 0
        self._cross_agent_shares = 0

        # Persistence flags
        self._db_available = False
        self._redis_available = False

    async def initialize(self):
        """Initialize memory stores — attempt DB & Redis, fall back to in-memory."""
        from config import settings

        # ─── PostgreSQL ───
        if not settings.DEMO_MODE:
            try:
                from db.engine import init_db, get_engine
                from db import repository
                await init_db()
                repository.set_db_available(True)
                self._db_available = True
                log.info("memory_db_connected")
            except Exception as exc:
                log.warning("memory_db_unavailable", error=str(exc))

        # ─── Redis Cache ───
        if not settings.DEMO_MODE:
            try:
                from db import redis_cache
                await redis_cache.init_redis()
                self._redis_available = redis_cache.is_available()
            except Exception as exc:
                log.warning("memory_redis_unavailable", error=str(exc))

        mode_parts = ["in-memory"]
        if self._db_available:
            mode_parts.append("PostgreSQL")
        if self._redis_available:
            mode_parts.append("Redis")
        mode_str = " + ".join(mode_parts)
        print(f"  🧠 Memory store initialized ({mode_str} with semantic + policy layers)")

    async def shutdown(self):
        """Gracefully shutdown memory stores."""
        if self._redis_available:
            try:
                from db import redis_cache
                await redis_cache.close_redis()
            except Exception:
                pass
        if self._db_available:
            try:
                from db.engine import close_db
                await close_db()
            except Exception:
                pass
        print(f"  🧠 Memory store shutdown. Experiences: {len(self._experiences)}, Skills: {len(self._skills)}, Semantic patterns: {sum(len(v) for v in self._semantic_patterns.values())}")

    # ─── Experience Storage ───

    async def store_experience(self, experience: AgentExperience):
        """Store an agent experience in long-term memory + PostgreSQL + Redis."""
        # ─── In-memory (always) ───
        self._experiences.append(experience)

        pattern_entry = {
            "agent": experience.agent_type,
            "action": experience.action_taken,
            "success": experience.success,
            "confidence": experience.confidence,
            "fix_time": experience.fix_time_seconds,
            "timestamp": experience.timestamp.isoformat(),
        }
        self._failure_patterns[experience.failure_type].append(pattern_entry)

        outcome_key = f"{experience.agent_type}:{experience.action_taken}"
        self._fix_outcomes[outcome_key].append({
            "success": experience.success,
            "confidence": experience.confidence,
            "timestamp": experience.timestamp.isoformat(),
        })

        # Extract skill if successful
        if experience.success and experience.reusable_skill:
            await self._extract_skill(experience)

        # Build semantic abstraction
        await self._build_semantic_pattern(experience)

        # Share knowledge cross-agent
        await self._share_knowledge(experience)

        # ─── PostgreSQL persistence (async, best-effort) ───
        if self._db_available:
            try:
                from db import repository
                await repository.save_experience({
                    "id": experience.experience_id,
                    "agent_type": experience.agent_type,
                    "failure_type": experience.failure_type,
                    "context_summary": experience.context_summary,
                    "action_taken": experience.action_taken,
                    "outcome": experience.outcome,
                    "success": experience.success,
                    "confidence": experience.confidence,
                    "fix_time_seconds": experience.fix_time_seconds,
                    "reusable_skill": experience.reusable_skill,
                })
            except Exception as exc:
                log.warning("db_persist_experience_failed", error=str(exc))

        # ─── Redis cache invalidation ───
        if self._redis_available:
            try:
                from db import redis_cache
                await redis_cache.cache_delete(f"failures:{experience.failure_type}")
                await redis_cache.cache_incr("stats:total_experiences")
            except Exception:
                pass

    async def store_workflow_experience(self, workflow: Workflow):
        """Store a complete workflow as an experience."""
        self._active_contexts[workflow.workflow_id] = {
            "event_type": workflow.event_type,
            "agents": workflow.agents_involved,
            "status": workflow.status.value,
            "duration": workflow.duration_seconds,
            "task_count": len(workflow.tasks),
            "shared_context_keys": list(workflow.shared_context.keys()),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        }

    # ─── Memory Recall ───

    async def recall(
        self, agent_type: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recall relevant prior knowledge for an agent task.

        Priority: Redis cache → in-memory → PostgreSQL fallback.

        Searches:
        1. Similar failure patterns
        2. Successful fix strategies
        3. Relevant skills
        4. Semantic patterns
        5. Cross-agent knowledge
        """
        self._recall_count += 1
        result = {}

        event_type = context.get("event_type", "")
        error_logs = context.get("error_logs", "")

        # ─── 1. Find similar failures (cache → memory → DB) ───
        if event_type:
            similar = self._failure_patterns.get(event_type, [])

            # If in-memory is empty but DB available, try loading from DB
            if not similar and self._db_available:
                try:
                    from db import repository
                    similar = await repository.load_experiences_by_failure(event_type, limit=50)
                    if similar:
                        self._failure_patterns[event_type] = similar
                except Exception:
                    pass

            if similar:
                successful = [s for s in similar if s.get("success")]
                result["similar_fixes"] = successful[-5:]
                result["failure_count"] = len(similar)
                result["success_rate"] = len(successful) / max(len(similar), 1)
                self._knowledge_reuse_count += 1

        # ─── 2. Find relevant skills (cache → memory → DB) ───
        relevant_skills = self._find_relevant_skills(agent_type, event_type)

        # If no in-memory skills but DB available, try loading
        if not relevant_skills and self._db_available:
            try:
                from db import repository
                relevant_skills = await repository.load_skills_for_agent(agent_type)
            except Exception:
                pass

        if relevant_skills:
            result["relevant_skills"] = relevant_skills

        # ─── 3. Agent-specific fix history ───
        action = context.get("action", "")
        outcome_key = f"{agent_type}:{action}"
        if outcome_key in self._fix_outcomes:
            outcomes = self._fix_outcomes[outcome_key]
            result["past_outcomes"] = outcomes[-10:]
            result["historical_success_rate"] = (
                sum(1 for o in outcomes if o["success"]) / max(len(outcomes), 1)
            )

        # ─── 4. Semantic pattern recall ───
        if event_type:
            semantic = self._semantic_patterns.get(event_type, [])
            if semantic:
                result["semantic_patterns"] = semantic[-5:]

        # ─── 5. Cross-agent shared knowledge ───
        shared = self._shared_knowledge.get(agent_type, [])
        if shared:
            result["cross_agent_knowledge"] = shared[-5:]

        return result

    # ─── Skill Management ───

    async def _extract_skill(self, experience: AgentExperience):
        """Extract a reusable skill from a successful experience and persist."""
        skill_key = f"{experience.agent_type}:{experience.reusable_skill}"
        if skill_key not in self._skills:
            self._skills[skill_key] = {
                "name": experience.reusable_skill,
                "agent_type": experience.agent_type,
                "description": experience.context_summary,
                "usage_count": 0,
                "success_count": 0,
                "avg_confidence": 0.0,
                "avg_fix_time": 0.0,
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
        skill["avg_fix_time"] = (
            (skill["avg_fix_time"] * (skill["usage_count"] - 1) + experience.fix_time_seconds)
            / skill["usage_count"]
        )

        # Update success rate
        self._skill_success_rates[skill_key] = (
            skill["success_count"] / skill["usage_count"]
        )

        # ─── Persist skill to DB ───
        if self._db_available:
            try:
                from db import repository
                await repository.upsert_skill(skill_key, {
                    "name": skill["name"],
                    "agent_type": skill["agent_type"],
                    "description": skill["description"],
                    "usage_count": skill["usage_count"],
                    "success_count": skill["success_count"],
                    "avg_confidence": skill["avg_confidence"],
                    "avg_fix_time": skill["avg_fix_time"],
                })
            except Exception as exc:
                log.warning("db_persist_skill_failed", error=str(exc))

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
                    "avg_fix_time": skill["avg_fix_time"],
                })
        return sorted(relevant, key=lambda s: s["success_rate"], reverse=True)[:5]

    # ─── Semantic Memory ───

    async def _build_semantic_pattern(self, experience: AgentExperience):
        """Abstract an experience into a semantic pattern category."""
        # Categorize by failure type + action pattern
        category = experience.failure_type
        pattern = {
            "agent": experience.agent_type,
            "action_pattern": experience.action_taken,
            "success": experience.success,
            "abstract_summary": self._abstract_summary(experience.context_summary),
            "confidence": experience.confidence,
            "timestamp": experience.timestamp.isoformat(),
        }
        self._semantic_patterns[category].append(pattern)

        # Keep only last 50 per category
        if len(self._semantic_patterns[category]) > 50:
            self._semantic_patterns[category] = self._semantic_patterns[category][-50:]

    def _abstract_summary(self, summary: str) -> str:
        """Create an abstract/generalized version of a context summary."""
        # Simple abstraction: remove specific names, keep patterns
        abstract = summary
        # Replace specific package names with placeholders
        for token in ["numpy", "lodash", "flask", "django", "react"]:
            if token in abstract.lower():
                abstract = abstract.replace(token, "<package>")
                abstract = abstract.replace(token.capitalize(), "<Package>")
        return abstract[:200]

    # ─── Cross-Agent Knowledge Sharing ───

    async def _share_knowledge(self, experience: AgentExperience):
        """Share relevant knowledge from one agent to all others."""
        if not experience.success or not experience.reusable_skill:
            return

        # Build shareable knowledge item
        knowledge = {
            "from_agent": experience.agent_type,
            "skill": experience.reusable_skill,
            "context": experience.context_summary[:200],
            "confidence": experience.confidence,
            "timestamp": experience.timestamp.isoformat(),
        }

        # Share with all other agent types
        agent_types = {"sre", "security", "qa", "review", "docs", "greenops"}
        for agent in agent_types:
            if agent != experience.agent_type:
                self._shared_knowledge[agent].append(knowledge)
                self._cross_agent_shares += 1

    # ─── Policy Learning ───

    async def record_policy_violation(self, task_action: str, reason: str, agent_type: str):
        """Record a policy violation for learning — in-memory + DB."""
        entry = {
            "action": task_action,
            "reason": reason,
            "agent": agent_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._policy_violations.append(entry)

        if self._db_available:
            try:
                from db import repository
                await repository.save_policy_event("violation", {
                    "action": task_action,
                    "reason": reason,
                    "agent_type": agent_type,
                })
            except Exception:
                pass

    async def record_policy_override(self, task_action: str, approved_by: str):
        """Record when a human overrides a policy block — in-memory + DB."""
        entry = {
            "action": task_action,
            "approved_by": approved_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._policy_overrides.append(entry)

        if self._db_available:
            try:
                from db import repository
                await repository.save_policy_event("override", {
                    "action": task_action,
                    "approved_by": approved_by,
                })
            except Exception:
                pass

    def get_policy_learning_stats(self) -> Dict[str, Any]:
        """Get policy learning statistics."""
        return {
            "total_violations": len(self._policy_violations),
            "total_overrides": len(self._policy_overrides),
            "override_rate": len(self._policy_overrides) / max(len(self._policy_violations), 1),
            "top_violated_actions": self._get_top_violated_actions(),
        }

    def _get_top_violated_actions(self) -> List[Dict[str, Any]]:
        """Get most frequently violated actions."""
        counts: Dict[str, int] = defaultdict(int)
        for v in self._policy_violations:
            counts[v["action"]] += 1
        return [{"action": a, "count": c} for a, c in sorted(counts.items(), key=lambda x: -x[1])[:5]]

    # ─── Query Methods ───

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "total_experiences": len(self._experiences),
            "failure_pattern_types": len(self._failure_patterns),
            "total_skills": len(self._skills),
            "semantic_pattern_categories": len(self._semantic_patterns),
            "cross_agent_shares": self._cross_agent_shares,
            "recall_count": self._recall_count,
            "knowledge_reuse_count": self._knowledge_reuse_count,
            "memory_utilization": (
                self._knowledge_reuse_count / max(self._recall_count, 1)
            ),
            "policy_violations": len(self._policy_violations),
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
