"""
AutoForge Database Tables — SQLAlchemy ORM models for persistence.

Maps the in-memory domain models to PostgreSQL tables:
- experiences: Agent learning experiences
- skills: Extracted reusable remediation strategies
- workflows: Workflow execution records
- workflow_tasks: Individual agent tasks within workflows
- policy_events: Policy violations and overrides
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from db.engine import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())[:12]


class ExperienceRow(Base):
    """Persisted agent experience — long-term memory."""
    __tablename__ = "experiences"

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_type = Column(String(32), nullable=False, index=True)
    failure_type = Column(String(128), nullable=False, index=True)
    context_summary = Column(Text, default="")
    action_taken = Column(String(256), default="")
    outcome = Column(String(32), default="")
    success = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    fix_time_seconds = Column(Float, default=0.0)
    reusable_skill = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    __table_args__ = (
        Index("ix_exp_agent_failure", "agent_type", "failure_type"),
    )


class SkillRow(Base):
    """Persisted reusable skill — derived from successful experiences."""
    __tablename__ = "skills"

    id = Column(String(64), primary_key=True)  # "agent_type:skill_name"
    name = Column(String(256), nullable=False)
    agent_type = Column(String(32), nullable=False, index=True)
    description = Column(Text, default="")
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    avg_fix_time = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class WorkflowRow(Base):
    """Persisted workflow — execution history."""
    __tablename__ = "workflows"

    workflow_id = Column(String(36), primary_key=True, default=_uuid)
    event_type = Column(String(64), nullable=False, index=True)
    project_id = Column(String(128), nullable=False, index=True)
    project_name = Column(String(256), default="")
    ref = Column(String(128), default="main")
    status = Column(String(32), default="pending", index=True)
    agents_involved = Column(JSONB, default=list)
    reasoning_chain = Column(JSONB, default=list)
    timeline = Column(JSONB, default=list)
    shared_context = Column(JSONB, default=dict)
    trigger_payload = Column(JSONB, default=dict)
    result = Column(JSONB, default=dict)
    retry_history = Column(JSONB, default=list)  # NEW: real retry tracking
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    tasks = relationship("WorkflowTaskRow", back_populates="workflow", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_wf_status_created", "status", "created_at"),
    )


class WorkflowTaskRow(Base):
    """Persisted agent task within a workflow."""
    __tablename__ = "workflow_tasks"

    task_id = Column(String(36), primary_key=True, default=_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.workflow_id"), nullable=False, index=True)
    agent_type = Column(String(32), nullable=False, index=True)
    action = Column(String(256), default="")
    priority = Column(String(16), default="medium")
    status = Column(String(24), default="queued")
    dependencies = Column(JSONB, default=list)
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    reasoning = Column(JSONB, default=dict)
    confidence = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    workflow = relationship("WorkflowRow", back_populates="tasks")


class PolicyEventRow(Base):
    """Persisted policy violation or override for learning."""
    __tablename__ = "policy_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    event_kind = Column(String(16), nullable=False, index=True)  # "violation" | "override"
    action = Column(String(256), default="")
    reason = Column(Text, default="")
    agent_type = Column(String(32), nullable=True)
    approved_by = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
