"""initial schema — experiences, skills, workflows, tasks, policy_events

Revision ID: 0001
Revises: None
Create Date: 2026-03-03

Creates the five core AutoForge tables for persistent memory.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── experiences ──
    op.create_table(
        "experiences",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agent_type", sa.String(32), nullable=False, index=True),
        sa.Column("failure_type", sa.String(128), nullable=False, index=True),
        sa.Column("context_summary", sa.Text, nullable=True),
        sa.Column("action_taken", sa.Text, nullable=True),
        sa.Column("outcome", sa.Text, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, default=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("fix_time_seconds", sa.Float, nullable=True),
        sa.Column("reusable_skill", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── skills ──
    op.create_table(
        "skills",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agent_type", sa.String(32), nullable=False, index=True),
        sa.Column("skill_name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("use_count", sa.Integer, nullable=False, default=0),
        sa.Column("avg_confidence", sa.Float, nullable=True),
        sa.Column("avg_fix_time", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── workflows ──
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, default="pending"),
        sa.Column("retry_history", postgresql.JSON, nullable=True),
        sa.Column("shared_context", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── workflow_tasks ──
    op.create_table(
        "workflow_tasks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workflow_id", sa.String(64), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_type", sa.String(32), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, default="pending"),
        sa.Column("dependencies", postgresql.JSON, nullable=True),
        sa.Column("result", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── policy_events ──
    op.create_table(
        "policy_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(32), nullable=False, index=True),
        sa.Column("action", sa.String(256), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("agent_type", sa.String(32), nullable=True),
        sa.Column("approved_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("policy_events")
    op.drop_table("workflow_tasks")
    op.drop_table("workflows")
    op.drop_table("skills")
    op.drop_table("experiences")
