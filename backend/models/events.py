"""
AutoForge Event Models — Structured event types for the system.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Supported event types in the AutoForge system."""
    PIPELINE_FAILURE = "pipeline_failure"
    PIPELINE_SUCCESS = "pipeline_success"
    MERGE_REQUEST_OPENED = "merge_request_opened"
    MERGE_REQUEST_UPDATED = "merge_request_updated"
    MERGE_REQUEST_MERGED = "merge_request_merged"
    PUSH = "push"
    SECURITY_ALERT = "security_alert"
    DEPENDENCY_ALERT = "dependency_alert"
    ISSUE_CREATED = "issue_created"
    MANUAL_TRIGGER = "manual_trigger"


class GitLabEvent(BaseModel):
    """Raw GitLab webhook event."""
    event_type: str
    payload: Dict[str, Any]
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NormalizedEvent(BaseModel):
    """Normalized event ready for brain processing."""
    event_type: EventType
    source: str = "gitlab"
    project_id: str
    project_name: str = ""
    ref: str = "main"
    payload: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_id(self) -> str:
        return f"{self.event_type.value}_{self.project_id}_{int(self.timestamp.timestamp())}"
