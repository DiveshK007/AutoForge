"""
AutoForge Webhook API — GitLab event ingestion endpoints.
Receives pipeline, merge request, and security events from GitLab.

In production mode (DEMO_MODE=False), heavy processing is dispatched
to Celery workers. In demo mode, events are processed in-process.
"""

import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Request

from brain.orchestrator import CommandBrain
from integrations.event_normalizer import EventNormalizer
from models.events import (
    GitLabEvent,
    NormalizedEvent,
    EventType,
)
from middleware.auth import AuthContext, require_role
from logging_config import get_logger

router = APIRouter()
normalizer = EventNormalizer()
log = get_logger("webhooks")


def _dispatch_to_celery(event_data: dict) -> str:
    """Dispatch event processing to Celery worker. Returns task ID."""
    from worker import process_event_task
    result = process_event_task.delay(event_data)
    log.info("celery_dispatched", celery_task_id=result.id, event_type=event_data.get("event_type"))
    return result.id


@router.post("/gitlab")
async def receive_gitlab_webhook(
    request: Request,
    x_gitlab_token: str | None = Header(None, alias="X-Gitlab-Token"),
    x_gitlab_event: str | None = Header(None, alias="X-Gitlab-Event"),
    x_gitlab_signature: str | None = Header(None, alias="X-Gitlab-Signature"),
):
    """
    Receive and process GitLab webhook events.

    Supported events:
    - Pipeline Hook (pipeline failures)
    - Merge Request Hook (new MRs, updates)
    - Push Hook (code changes)
    - Note Hook (comments)
    """
    # Read raw body once for both HMAC verification and JSON parsing
    raw_body = await request.body()
    brain: CommandBrain = request.app.state.brain

    # ─── Verify webhook authenticity ───
    from config import settings
    secret = settings.GITLAB_WEBHOOK_SECRET
    if secret:
        # Method 1: HMAC-SHA256 signature (preferred — GitLab sends X-Gitlab-Signature)
        if x_gitlab_signature:
            expected = hmac.new(
                secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, x_gitlab_signature):
                log.warning("webhook_signature_mismatch", header="X-Gitlab-Signature")
                raise HTTPException(status_code=401, detail="Invalid HMAC signature")
        # Method 2: Simple secret token (fallback — older GitLab versions)
        elif x_gitlab_token:
            if x_gitlab_token != secret:
                log.warning("webhook_token_mismatch")
                raise HTTPException(status_code=401, detail="Invalid webhook token")
        else:
            # Secret configured but no authentication header provided
            log.warning("webhook_no_auth_header")
            raise HTTPException(status_code=401, detail="Missing authentication header")

    body = __import__("json").loads(raw_body)

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

    # ─── Enrich MR events with diff (best-effort) ───
    normalized = await normalizer.enrich_with_diff(normalized)

    # ─── Route: Celery (production) vs in-process (demo) ───
    if not settings.DEMO_MODE and _celery_available():
        celery_task_id = _dispatch_to_celery(normalized.model_dump(mode="json"))
        return {
            "status": "accepted",
            "dispatch": "celery",
            "celery_task_id": celery_task_id,
            "event_type": normalized.event_type.value,
            "timestamp": normalized.timestamp.isoformat(),
        }

    # In-process (demo or Celery unavailable)
    workflow_id = await brain.ingest_event(normalized)

    return {
        "status": "accepted",
        "workflow_id": workflow_id,
        "event_type": normalized.event_type.value,
        "timestamp": normalized.timestamp.isoformat(),
    }


@router.post("/test-trigger")
async def test_trigger(request: Request, _auth: AuthContext = Depends(require_role("operator"))):
    """
    Manual test trigger for development.
    Accepts a simulated event payload for testing agent workflows.
    Supports both {event_type: ...} and {scenario: ...} formats.
    """
    body = await request.json()
    brain: CommandBrain = request.app.state.brain

    # Support both formats: {scenario: "pipeline_failure_missing_dep"} or {event_type: "pipeline_failure"}
    scenario = body.get("scenario", "")
    event_type = body.get("event_type", "")

    # Map scenario names to event types
    scenario_map = {
        "pipeline_failure_missing_dep": "pipeline_failure",
        "security_vulnerability": "security_alert",
        "merge_request_opened": "merge_request_opened",
        "inefficient_pipeline": "pipeline_success",
    }

    if scenario and not event_type:
        event_type = scenario_map.get(scenario, "pipeline_failure")

    if not event_type:
        event_type = "pipeline_failure"

    normalized = NormalizedEvent(
        event_type=EventType(event_type),
        source="manual_test",
        project_id=body.get("project_id", "test-project"),
        project_name=body.get("project_name", "Test Project"),
        ref=body.get("ref", "main"),
        payload=body.get("payload", {"scenario": scenario or event_type}),
        metadata=body.get("metadata", {}),
        timestamp=datetime.now(timezone.utc),
    )

    # ─── Route: Celery (production) vs in-process ───
    from config import settings
    if not settings.DEMO_MODE and _celery_available():
        celery_task_id = _dispatch_to_celery(normalized.model_dump(mode="json"))
        return {
            "status": "triggered",
            "dispatch": "celery",
            "celery_task_id": celery_task_id,
            "event_type": event_type,
            "scenario": scenario or event_type,
        }

    workflow_id = await brain.ingest_event(normalized)

    return {
        "status": "triggered",
        "workflow_id": workflow_id,
        "event_type": event_type,
        "scenario": scenario or event_type,
    }


def _celery_available() -> bool:
    """Check if Celery broker is reachable."""
    try:
        from worker import celery_app
        conn = celery_app.connection()
        conn.ensure_connection(max_retries=0, timeout=1)
        conn.close()
        return True
    except Exception:
        return False
