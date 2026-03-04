"""
AutoForge GitLab Integration — Webhook processor.

Parses incoming GitLab webhook payloads, verifies tokens, and
produces NormalizedEvent objects ready for the CommandBrain.
"""

import hmac
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from config import settings
from models.events import EventType, NormalizedEvent

logger = logging.getLogger("autoforge.integrations.gitlab.webhooks")

# Map GitLab webhook event kinds to EventType
_EVENT_KIND_MAP: Dict[str, str] = {
    "Pipeline Hook": "pipeline",
    "Merge Request Hook": "merge_request",
    "Push Hook": "push",
    "Tag Push Hook": "push",
    "Note Hook": "note",
    "Issue Hook": "issue",
}


class WebhookProcessor:
    """
    Enterprise-grade GitLab webhook processor.

    Responsibilities
    ─────────────────
    1. Validate the ``X-Gitlab-Token`` header.
    2. Identify the event kind from ``X-Gitlab-Event``.
    3. Normalise the raw payload into a *NormalizedEvent*.
    4. Return ``(event, raw_payload)`` so callers can persist the raw blob.
    """

    def __init__(self, webhook_secret: Optional[str] = None) -> None:
        self._secret = webhook_secret or settings.GITLAB_WEBHOOK_SECRET

    # ── public API ──────────────────────────────────────────────

    def validate_token(self, token: Optional[str]) -> bool:
        """Check the X-Gitlab-Token header matches the configured secret."""
        if not self._secret:
            logger.warning("GITLAB_WEBHOOK_SECRET is not set — accepting all hooks")
            return True
        if not token:
            return False
        return hmac.compare_digest(token, self._secret)

    def parse(
        self, event_header: str, payload: Dict[str, Any],
    ) -> Tuple[Optional[NormalizedEvent], Dict[str, Any]]:
        """
        Parse a raw GitLab webhook payload.

        Returns ``(NormalizedEvent | None, raw_payload)``.
        ``None`` is returned when the event kind is unrecognised.
        """
        kind = _EVENT_KIND_MAP.get(event_header)
        if kind is None:
            logger.info("Ignoring unhandled webhook kind: %s", event_header)
            return None, payload

        normalizer = getattr(self, f"_normalize_{kind}", None)
        if normalizer is None:
            logger.warning("No normalizer for kind=%s", kind)
            return None, payload

        try:
            event = normalizer(payload)
            logger.info(
                "Webhook normalised: kind=%s type=%s project=%s",
                kind, event.event_type.value, event.project_id,
            )
            return event, payload
        except Exception:
            logger.exception("Failed to normalise webhook kind=%s", kind)
            return None, payload

    # ── private normalisers ─────────────────────────────────────

    def _normalize_pipeline(self, data: Dict[str, Any]) -> NormalizedEvent:
        attrs = data.get("object_attributes", {})
        status = attrs.get("status", "")
        event_type = (
            EventType.PIPELINE_FAILURE if status == "failed"
            else EventType.PIPELINE_SUCCESS
        )
        payload = {
            "pipeline_id": attrs.get("id"),
            "ref": attrs.get("ref"),
            "status": status,
            "sha": attrs.get("sha"),
            "source": attrs.get("source"),
            "stages": attrs.get("stages", []),
            "created_at": attrs.get("created_at"),
            "finished_at": attrs.get("finished_at"),
        }
        return NormalizedEvent(
            event_type=event_type,
            project_id=str(data.get("project", {}).get("id", "")),
            source="gitlab_webhook",
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )

    def _normalize_merge_request(self, data: Dict[str, Any]) -> NormalizedEvent:
        attrs = data.get("object_attributes", {})
        action = attrs.get("action", "")
        if action == "merge":
            event_type = EventType.MERGE_REQUEST_MERGED
        elif action == "update":
            event_type = EventType.MERGE_REQUEST_UPDATED
        else:
            event_type = EventType.MERGE_REQUEST_OPENED

        payload = {
            "merge_request_iid": attrs.get("iid"),
            "action": action,
            "title": attrs.get("title"),
            "source_branch": attrs.get("source_branch"),
            "target_branch": attrs.get("target_branch"),
            "author": data.get("user", {}).get("username"),
            "state": attrs.get("state"),
            "url": attrs.get("url"),
        }
        return NormalizedEvent(
            event_type=event_type,
            project_id=str(data.get("project", {}).get("id", "")),
            source="gitlab_webhook",
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )

    def _normalize_push(self, data: Dict[str, Any]) -> NormalizedEvent:
        payload = {
            "ref": data.get("ref"),
            "before": data.get("before"),
            "after": data.get("after"),
            "user": data.get("user_username"),
            "total_commits_count": data.get("total_commits_count", 0),
            "commits": [
                {
                    "id": c.get("id"),
                    "message": c.get("message"),
                    "author": c.get("author", {}).get("name"),
                }
                for c in (data.get("commits") or [])[:10]
            ],
        }
        return NormalizedEvent(
            event_type=EventType.PUSH,
            project_id=str(data.get("project_id", data.get("project", {}).get("id", ""))),
            source="gitlab_webhook",
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )

    def _normalize_note(self, data: Dict[str, Any]) -> Optional[NormalizedEvent]:
        """Notes (comments) are mapped to MR_UPDATED if attached to an MR."""
        mr = data.get("merge_request")
        if not mr:
            return None
        payload = {
            "merge_request_iid": mr.get("iid"),
            "action": "note",
            "note": data.get("object_attributes", {}).get("note", "")[:500],
            "author": data.get("user", {}).get("username"),
        }
        return NormalizedEvent(
            event_type=EventType.MERGE_REQUEST_UPDATED,
            project_id=str(data.get("project", {}).get("id", "")),
            source="gitlab_webhook",
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )

    def _normalize_issue(self, data: Dict[str, Any]) -> NormalizedEvent:
        attrs = data.get("object_attributes", {})
        payload = {
            "issue_iid": attrs.get("iid"),
            "action": attrs.get("action"),
            "title": attrs.get("title"),
            "description": (attrs.get("description") or "")[:1000],
            "labels": [l.get("title") for l in (data.get("labels") or [])],
            "author": data.get("user", {}).get("username"),
        }
        return NormalizedEvent(
            event_type=EventType.ISSUE_CREATED,
            project_id=str(data.get("project", {}).get("id", "")),
            source="gitlab_webhook",
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )
