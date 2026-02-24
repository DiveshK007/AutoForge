"""
AutoForge GitLab Integration — Enterprise-grade GitLab API integration layer.

This package provides a modular, async, secure, and demo-safe abstraction
over the GitLab REST API.  Every call routes through a single authenticated
client with retry logic, rate-limit awareness, structured logging, and
telemetry hooks.

Architecture:
    Agent → Tool Gateway → Integration Layer → GitLab REST API
                                ↓
                         Telemetry Collector
"""

from integrations.gitlab.gitlab_client import GitLabAPIClient
from integrations.gitlab.pipelines import PipelineService
from integrations.gitlab.merge_requests import MergeRequestService
from integrations.gitlab.repository import RepositoryService
from integrations.gitlab.commits import CommitService
from integrations.gitlab.security import SecurityService
from integrations.gitlab.webhooks import WebhookProcessor
from integrations.gitlab.event_normalizer import GitLabEventNormalizer
from integrations.gitlab.demo_mode import DemoModeSimulator
from integrations.gitlab.models import (
    PipelineInfo,
    JobInfo,
    MergeRequestInfo,
    FileContent,
    BranchInfo,
    CommitResult,
    VulnerabilityInfo,
    GitLabAPIResponse,
)

__all__ = [
    "GitLabAPIClient",
    "PipelineService",
    "MergeRequestService",
    "RepositoryService",
    "CommitService",
    "SecurityService",
    "WebhookProcessor",
    "GitLabEventNormalizer",
    "DemoModeSimulator",
    # Models
    "PipelineInfo",
    "JobInfo",
    "MergeRequestInfo",
    "FileContent",
    "BranchInfo",
    "CommitResult",
    "VulnerabilityInfo",
    "GitLabAPIResponse",
]
