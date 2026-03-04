"""
AutoForge Database Repository — CRUD operations for persistent memory.

Acts as the data-access layer between MemoryStore and PostgreSQL.
Uses SQLAlchemy async sessions.
All methods are safe to call when the DB is unavailable (return empty / no-op).
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, func, desc

from db.engine import get_session_factory
from db.tables import ExperienceRow, SkillRow, WorkflowRow, WorkflowTaskRow, PolicyEventRow
from logging_config import get_logger

log = get_logger("db.repository")

_db_available = False


def set_db_available(val: bool):
    global _db_available
    _db_available = val


def is_db_available() -> bool:
    return _db_available


# ─── Experience CRUD ────────────────────────────────────────────

async def save_experience(data: dict) -> Optional[str]:
    """Persist an experience to PostgreSQL. Returns row ID or None."""
    if not _db_available:
        return None
    try:
        factory = get_session_factory()
        async with factory() as session:
            row = ExperienceRow(**data)
            session.add(row)
            await session.commit()
            return row.id
    except Exception as exc:
        log.warning("save_experience_failed", error=str(exc))
        return None


async def load_experiences_by_failure(failure_type: str, limit: int = 50) -> List[dict]:
    """Load experiences matching a failure type."""
    if not _db_available:
        return []
    try:
        factory = get_session_factory()
        async with factory() as session:
            stmt = (
                select(ExperienceRow)
                .where(ExperienceRow.failure_type == failure_type)
                .order_by(desc(ExperienceRow.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "agent": r.agent_type,
                    "action": r.action_taken,
                    "success": r.success,
                    "confidence": r.confidence,
                    "fix_time": r.fix_time_seconds,
                    "timestamp": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]
    except Exception as exc:
        log.warning("load_experiences_failed", error=str(exc))
        return []


async def count_experiences() -> int:
    """Count total experiences."""
    if not _db_available:
        return 0
    try:
        factory = get_session_factory()
        async with factory() as session:
            stmt = select(func.count(ExperienceRow.id))
            result = await session.execute(stmt)
            return result.scalar_one_or_none() or 0
    except Exception:
        return 0


# ─── Skill CRUD ─────────────────────────────────────────────────

async def upsert_skill(skill_id: str, data: dict):
    """Insert or update a skill row."""
    if not _db_available:
        return
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(SkillRow, skill_id)
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                row = SkillRow(id=skill_id, **data)
                session.add(row)
            await session.commit()
    except Exception as exc:
        log.warning("upsert_skill_failed", error=str(exc))


async def load_skills_for_agent(agent_type: str) -> List[dict]:
    """Load skills for an agent type."""
    if not _db_available:
        return []
    try:
        factory = get_session_factory()
        async with factory() as session:
            stmt = (
                select(SkillRow)
                .where(SkillRow.agent_type == agent_type)
                .order_by(desc(SkillRow.success_count))
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "name": r.name,
                    "success_rate": r.success_count / max(r.usage_count, 1),
                    "usage_count": r.usage_count,
                    "confidence": r.avg_confidence,
                    "avg_fix_time": r.avg_fix_time,
                }
                for r in rows
            ]
    except Exception as exc:
        log.warning("load_skills_failed", error=str(exc))
        return []


# ─── Workflow CRUD ──────────────────────────────────────────────

async def save_workflow(data: dict) -> Optional[str]:
    """Persist a workflow snapshot."""
    if not _db_available:
        return None
    try:
        factory = get_session_factory()
        async with factory() as session:
            row = WorkflowRow(**data)
            session.add(row)
            await session.commit()
            return row.workflow_id
    except Exception as exc:
        log.warning("save_workflow_failed", error=str(exc))
        return None


async def update_workflow(workflow_id: str, data: dict):
    """Update an existing workflow row."""
    if not _db_available:
        return
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(WorkflowRow, workflow_id)
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
                await session.commit()
    except Exception as exc:
        log.warning("update_workflow_failed", error=str(exc))


async def load_workflow(workflow_id: str) -> Optional[dict]:
    """Load a single workflow by ID."""
    if not _db_available:
        return None
    try:
        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(WorkflowRow, workflow_id)
            if row:
                return {
                    "workflow_id": row.workflow_id,
                    "event_type": row.event_type,
                    "project_id": row.project_id,
                    "status": row.status,
                    "agents_involved": row.agents_involved or [],
                    "shared_context": row.shared_context or {},
                    "retry_history": row.retry_history or [],
                    "reasoning_chain": row.reasoning_chain or [],
                    "timeline": row.timeline or [],
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                }
    except Exception as exc:
        log.warning("load_workflow_failed", error=str(exc))
    return None


# ─── Policy Events ──────────────────────────────────────────────

async def save_policy_event(event_kind: str, data: dict):
    """Persist a policy violation or override."""
    if not _db_available:
        return
    try:
        factory = get_session_factory()
        async with factory() as session:
            row = PolicyEventRow(event_kind=event_kind, **data)
            session.add(row)
            await session.commit()
    except Exception as exc:
        log.warning("save_policy_event_failed", error=str(exc))


# ─── Workflow Task CRUD ─────────────────────────────────────────

async def save_workflow_task(workflow_id: str, data: dict) -> Optional[str]:
    """Persist or update a workflow task row."""
    if not _db_available:
        return None
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(WorkflowTaskRow, data.get("task_id"))
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
            else:
                row = WorkflowTaskRow(**data)
                session.add(row)
            await session.commit()
            return data.get("task_id")
    except Exception as exc:
        log.warning("save_workflow_task_failed", error=str(exc))
        return None


async def load_workflows(limit: int = 50, status: Optional[str] = None) -> List[dict]:
    """Load workflow history from the database."""
    if not _db_available:
        return []
    try:
        factory = get_session_factory()
        async with factory() as session:
            stmt = select(WorkflowRow).order_by(desc(WorkflowRow.created_at)).limit(limit)
            if status:
                stmt = stmt.where(WorkflowRow.status == status)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "workflow_id": r.workflow_id,
                    "event_type": r.event_type,
                    "project_id": r.project_id,
                    "project_name": r.project_name,
                    "status": r.status,
                    "agents_involved": r.agents_involved or [],
                    "reasoning_chain": r.reasoning_chain or [],
                    "timeline": r.timeline or [],
                    "retry_history": r.retry_history or [],
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in rows
            ]
    except Exception as exc:
        log.warning("load_workflows_failed", error=str(exc))
        return []
