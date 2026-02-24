"""
AutoForge Webhook API — GitLab event ingestion endpoints.
Receives pipeline, merge request, and security events from GitLab.
"""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Request

from brain.orchestrator import CommandBrain
from integrations.event_normalizer import EventNormalizer
from models.events import (
    GitLabEvent,
    NormalizedEvent,
    EventType,
)

router = APIRouter()
normalizer = EventNormalizer()


@router.post("/gitlab")
async def receive_gitlab_webhook(
    request: Request,
    x_gitlab_token: str | None = Header(None, alias="X-Gitlab-Token"),
    x_gitlab_event: str | None = Header(None, alias="X-Gitlab-Event"),
):
    """
    Receive and process GitLab webhook events.

    Supported events:
    - Pipeline Hook (pipeline failures)
    - Merge Request Hook (new MRs, updates)
    - Push Hook (code changes)
    - Note Hook (comments)
    """
    body = await request.json()
    brain: CommandBrain = request.app.state.brain

    # ─── Verify webhook token ───
    from config import settings
    if settings.GITLAB_WEBHOOK_SECRET and x_gitlab_token != settings.GITLAB_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    # ─── Parse raw event ───
    raw_event = GitLabEvent(
        event_type=x_gitlab_event or body.get("object_kind", "unknown"),
        payload=body,
        received_at=datetime.now(timezone.utc),
    )

    # ─── Normalize event ───
    normalized = normalizer.normalize(raw_event)

    if normalized is None:
        return {"status": "ignored", "reason": "Event type not actionable"}

    # ─── Route to Command Brain ───
    workflow_id = await brain.ingest_event(normalized)

    return {
        "status": "accepted",
        "workflow_id": workflow_id,
        "event_type": normalized.event_type.value,
        "timestamp": normalized.timestamp.isoformat(),
    }


@router.post("/test-trigger")
async def test_trigger(request: Request):
    """
    Manual test trigger for development.
    Accepts a simulated event payload for testing agent workflows.
    """
    body = await request.json()
    brain: CommandBrain = request.app.state.brain

    event_type = body.get("event_type", "pipeline_failure")
    normalized = NormalizedEvent(
        event_type=EventType(event_type),
        source="manual_test",
        project_id=body.get("project_id", "test-project"),
        project_name=body.get("project_name", "Test Project"),
        ref=body.get("ref", "main"),
        payload=body.get("payload", {}),
        metadata=body.get("metadata", {}),
        timestamp=datetime.now(timezone.utc),
    )

    workflow_id = await brain.ingest_event(normalized)

    return {
        "status": "triggered",
        "workflow_id": workflow_id,
        "event_type": event_type,
    }
