"""
AutoForge API Request / Response Schemas — Strict Pydantic validation.

Provides enterprise-grade request validation for all webhook and API inputs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Webhook Payloads ─────────────────────────────────

class GitLabPipelinePayload(BaseModel):
    """Validated GitLab pipeline webhook payload."""
    object_kind: str = Field(..., pattern=r"^(pipeline|build)$")
    object_attributes: Dict[str, Any] = Field(default_factory=dict)
    project: Dict[str, Any] = Field(default_factory=dict)
    commit: Optional[Dict[str, Any]] = None
    builds: Optional[List[Dict[str, Any]]] = None

    @field_validator("object_attributes")
    @classmethod
    def validate_object_attributes(cls, v: dict) -> dict:
        if "status" not in v:
            raise ValueError("object_attributes must contain 'status'")
        return v


class GitLabMergeRequestPayload(BaseModel):
    """Validated GitLab merge request webhook payload."""
    object_kind: str = Field(..., pattern=r"^merge_request$")
    object_attributes: Dict[str, Any] = Field(default_factory=dict)
    project: Dict[str, Any] = Field(default_factory=dict)
    user: Optional[Dict[str, Any]] = None
    changes: Optional[Dict[str, Any]] = None

    @field_validator("object_attributes")
    @classmethod
    def validate_mr_attributes(cls, v: dict) -> dict:
        required = {"state", "title"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"object_attributes missing required fields: {missing}")
        return v


class GitLabSecurityPayload(BaseModel):
    """Validated GitLab security alert webhook payload."""
    object_kind: Optional[str] = None
    event_type: Optional[str] = None
    vulnerability: Optional[Dict[str, Any]] = None
    project: Dict[str, Any] = Field(default_factory=dict)


class TestTriggerRequest(BaseModel):
    """Validated manual test trigger request."""
    scenario: Optional[str] = None
    event_type: Optional[str] = None
    project_id: str = "test-project"
    project_name: str = "Test Project"
    ref: str = "main"
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("scenario")
    @classmethod
    def validate_scenario(cls, v: Optional[str]) -> Optional[str]:
        valid = {
            None, "",
            "pipeline_failure_missing_dep",
            "security_vulnerability",
            "merge_request_opened",
            "inefficient_pipeline",
        }
        if v and v not in valid:
            raise ValueError(f"Unknown scenario: {v}. Valid: {valid - {None, ''}}")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: Optional[str]) -> Optional[str]:
        valid = {
            None, "",
            "pipeline_failure",
            "pipeline_success",
            "merge_request_opened",
            "merge_request_updated",
            "security_alert",
            "dependency_alert",
            "push",
            "issue_created",
            "manual_trigger",
        }
        if v and v not in valid:
            raise ValueError(f"Unknown event_type: {v}. Valid: {valid - {None, ''}}")
        return v


# ─── API Response Schemas ─────────────────────────────

class WebhookAcceptedResponse(BaseModel):
    """Response for accepted webhook events."""
    status: str = "accepted"
    workflow_id: str
    event_type: str
    timestamp: str


class TestTriggerResponse(BaseModel):
    """Response for test trigger requests."""
    status: str = "triggered"
    workflow_id: str
    event_type: str
    scenario: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "operational"
    system: str = "AutoForge"
    version: str
    brain: str = "online"
    agents: str = "standing_by"


class ReadinessResponse(BaseModel):
    """Readiness probe response."""
    ready: bool
    checks: Dict[str, bool]
    version: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


class ExplainResponse(BaseModel):
    """Response from the explain endpoint."""
    workflow_id: str
    explanation: str
    format: str = "markdown"
    agents_involved: Optional[List[str]] = None
    task_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    status: Optional[str] = None
    reasoning_depth: Optional[int] = None
    confidence: Optional[float] = None
