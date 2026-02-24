"""
AutoForge GitLab Integration — Pydantic response models.

Every GitLab API response is deserialized into a typed model.
Agents and the tool gateway never work with raw dicts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Enums ─────────────────────────────────────────────────────────────────────

class PipelineStatus(str, Enum):
    CREATED = "created"
    WAITING = "waiting_for_resource"
    PREPARING = "preparing"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    SKIPPED = "skipped"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class MergeRequestState(str, Enum):
    OPENED = "opened"
    CLOSED = "closed"
    MERGED = "merged"
    LOCKED = "locked"


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


# ─── Base Response ─────────────────────────────────────────────────────────────

class GitLabAPIResponse(BaseModel):
    """Wrapper for all GitLab API responses — provides success/error context."""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: int = 200
    request_id: Optional[str] = None
    demo_mode: bool = False

    @classmethod
    def ok(cls, data: Dict[str, Any], demo: bool = False) -> "GitLabAPIResponse":
        return cls(success=True, data=data, demo_mode=demo)

    @classmethod
    def fail(cls, error: str, status_code: int = 500) -> "GitLabAPIResponse":
        return cls(success=False, error=error, status_code=status_code)


# ─── Pipeline Models ──────────────────────────────────────────────────────────

class JobInfo(BaseModel):
    """A single CI/CD job."""
    id: int
    name: str
    stage: str
    status: str
    duration: Optional[float] = None
    web_url: Optional[str] = None
    failure_reason: Optional[str] = None
    runner_description: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class PipelineInfo(BaseModel):
    """Pipeline metadata."""
    id: int
    iid: Optional[int] = None
    project_id: int
    status: PipelineStatus = PipelineStatus.PENDING
    ref: str = "main"
    sha: Optional[str] = None
    web_url: Optional[str] = None
    source: Optional[str] = None
    duration: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    finished_at: Optional[str] = None
    jobs: List[JobInfo] = []


# ─── Merge Request Models ─────────────────────────────────────────────────────

class DiffInfo(BaseModel):
    """A file diff in a merge request."""
    old_path: str
    new_path: str
    diff: str = ""
    new_file: bool = False
    renamed_file: bool = False
    deleted_file: bool = False


class MergeRequestInfo(BaseModel):
    """Merge request metadata."""
    id: int
    iid: int
    project_id: int
    title: str
    description: str = ""
    state: MergeRequestState = MergeRequestState.OPENED
    source_branch: str = ""
    target_branch: str = "main"
    web_url: Optional[str] = None
    author: Optional[str] = None
    labels: List[str] = []
    changes: List[DiffInfo] = []
    has_conflicts: bool = False
    created_at: Optional[str] = None
    merged_at: Optional[str] = None


# ─── Repository Models ────────────────────────────────────────────────────────

class FileContent(BaseModel):
    """File content from repository."""
    file_name: str
    file_path: str
    size: int = 0
    encoding: str = "base64"
    content: str = ""
    content_sha256: Optional[str] = None
    ref: str = "main"
    last_commit_id: Optional[str] = None

    @property
    def decoded_content(self) -> str:
        """Decode base64 content to string."""
        if self.encoding == "base64" and self.content:
            import base64
            return base64.b64decode(self.content).decode("utf-8")
        return self.content


class BranchInfo(BaseModel):
    """Branch metadata."""
    name: str
    protected: bool = False
    developers_can_push: bool = True
    developers_can_merge: bool = True
    web_url: Optional[str] = None
    commit_sha: Optional[str] = None


class CommitAction(BaseModel):
    """A single file action in a batch commit."""
    action: str = "update"  # create, update, delete, move
    file_path: str
    content: str = ""
    previous_path: Optional[str] = None
    encoding: str = "text"


class CommitResult(BaseModel):
    """Result of a commit operation."""
    id: str
    short_id: str = ""
    title: str = ""
    message: str = ""
    author_name: str = "AutoForge"
    author_email: str = "autoforge@system"
    web_url: Optional[str] = None
    created_at: Optional[str] = None
    stats: Dict[str, int] = {}


# ─── Security Models ──────────────────────────────────────────────────────────

class VulnerabilityInfo(BaseModel):
    """A security vulnerability finding."""
    id: int
    name: str
    description: str = ""
    severity: VulnerabilitySeverity = VulnerabilitySeverity.UNKNOWN
    confidence: Optional[str] = None
    scanner: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    identifiers: List[Dict[str, Any]] = []
    solution: Optional[str] = None
    state: str = "detected"
    project_id: Optional[int] = None


class DependencyAlert(BaseModel):
    """A dependency-level security alert."""
    dependency_name: str
    dependency_version: str
    vulnerability: str = ""
    severity: VulnerabilitySeverity = VulnerabilitySeverity.UNKNOWN
    fixed_version: Optional[str] = None
    cve_id: Optional[str] = None


# ─── Telemetry Envelope ───────────────────────────────────────────────────────

class APICallTelemetry(BaseModel):
    """Telemetry record for every integration-layer API call."""
    tool: str
    action: str
    agent: Optional[str] = None
    workflow_id: Optional[str] = None
    success: bool = True
    execution_time_ms: float = 0.0
    risk_score: float = 0.0
    status_code: int = 200
    demo_mode: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "action": self.action,
            "agent": self.agent,
            "workflow_id": self.workflow_id,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "risk_score": self.risk_score,
            "status_code": self.status_code,
            "demo_mode": self.demo_mode,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }
