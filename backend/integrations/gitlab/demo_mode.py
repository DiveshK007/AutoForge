"""
AutoForge GitLab Integration — Demo mode simulator.

When DEMO_MODE=True every service-layer call returns a deterministic,
precomputed response loaded from ``demo_scenarios/`` JSON files.
No network requests are made.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from integrations.gitlab.models import (
    BranchInfo,
    CommitResult,
    DependencyAlert,
    FileContent,
    JobInfo,
    MergeRequestInfo,
    PipelineInfo,
    PipelineStatus,
    MergeRequestState,
    VulnerabilityInfo,
    VulnerabilitySeverity,
)

logger = logging.getLogger("autoforge.integrations.gitlab.demo")

_DEMO_DIR = Path(__file__).resolve().parent.parent.parent.parent / "demo_scenarios"
_CACHE: Dict[str, Any] = {}


def _load_scenario(filename: str) -> Dict[str, Any]:
    """Load and cache a demo scenario JSON file."""
    if filename in _CACHE:
        return _CACHE[filename]

    path = _DEMO_DIR / filename
    if not path.exists():
        logger.warning("Demo scenario file not found: %s", path)
        return {}

    with open(path) as f:
        data = json.load(f)
    _CACHE[filename] = data
    return data


class DemoModeSimulator:
    """
    Provides deterministic, precomputed responses for every GitLab API
    operation used by AutoForge agents.
    """

    # ─── Pipeline Responses ────────────────────────────────────────────────

    @staticmethod
    def get_pipeline(project_id: str, pipeline_id: int) -> PipelineInfo:
        scenario = _load_scenario("pipeline_failure_missing_dep.json")
        payload = scenario.get("payload", {})
        return PipelineInfo(
            id=pipeline_id,
            project_id=int(project_id) if project_id.isdigit() else 1,
            status=PipelineStatus.FAILED,
            ref=payload.get("ref", "main"),
            sha=payload.get("commit_sha", "abc123"),
            web_url=payload.get("pipeline_url", ""),
            duration=payload.get("pipeline_duration", 180),
        )

    @staticmethod
    def get_pipeline_jobs(project_id: str, pipeline_id: int) -> List[JobInfo]:
        scenario = _load_scenario("pipeline_failure_missing_dep.json")
        raw_jobs = scenario.get("payload", {}).get("failed_jobs", [])
        jobs = []
        for j in raw_jobs:
            jobs.append(JobInfo(
                id=j.get("id", 101),
                name=j.get("name", "test"),
                stage=j.get("stage", "test"),
                status=j.get("status", "failed"),
                failure_reason="script_failure",
            ))
        # Add a passing job for realism
        jobs.append(JobInfo(id=100, name="lint", stage="lint", status="success"))
        return jobs

    @staticmethod
    def get_job_log(project_id: str, job_id: int) -> str:
        scenario = _load_scenario("pipeline_failure_missing_dep.json")
        return scenario.get("payload", {}).get("error_logs", "No logs available")

    @staticmethod
    def retry_pipeline(project_id: str, pipeline_id: int) -> PipelineInfo:
        return PipelineInfo(
            id=pipeline_id + 1,
            project_id=int(project_id) if project_id.isdigit() else 1,
            status=PipelineStatus.PENDING,
            ref="main",
        )

    @staticmethod
    def trigger_pipeline(project_id: str, ref: str) -> PipelineInfo:
        return PipelineInfo(
            id=999,
            project_id=int(project_id) if project_id.isdigit() else 1,
            status=PipelineStatus.CREATED,
            ref=ref,
        )

    # ─── Merge Request Responses ───────────────────────────────────────────

    @staticmethod
    def create_merge_request(
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
    ) -> MergeRequestInfo:
        return MergeRequestInfo(
            id=1001,
            iid=42,
            project_id=int(project_id) if project_id.isdigit() else 1,
            title=title,
            description=description,
            state=MergeRequestState.OPENED,
            source_branch=source_branch,
            target_branch=target_branch,
            web_url="https://gitlab.com/demo/project/-/merge_requests/42",
            labels=["autoforge", "automated-fix"],
        )

    @staticmethod
    def comment_on_mr(project_id: str, mr_iid: int, body: str) -> Dict[str, Any]:
        return {
            "id": 5001,
            "body": body,
            "author": {"username": "autoforge-bot"},
            "created_at": "2025-02-24T12:00:00Z",
        }

    @staticmethod
    def approve_mr(project_id: str, mr_iid: int) -> Dict[str, Any]:
        return {"id": mr_iid, "approved": True}

    @staticmethod
    def get_mr_changes(project_id: str, mr_iid: int) -> MergeRequestInfo:
        return MergeRequestInfo(
            id=1001,
            iid=mr_iid,
            project_id=int(project_id) if project_id.isdigit() else 1,
            title="AutoForge: Fix missing numpy dependency",
            state=MergeRequestState.OPENED,
            source_branch="autoforge/fix-pipeline-42",
            target_branch="main",
        )

    # ─── Repository Responses ──────────────────────────────────────────────

    @staticmethod
    def get_file(project_id: str, file_path: str, ref: str = "main") -> FileContent:
        import base64
        demo_content = {
            "requirements.txt": "flask==2.3.0\nrequests==2.31.0\npytest==7.4.0\n",
            "setup.py": "from setuptools import setup\nsetup(name='demo')\n",
        }
        content = demo_content.get(file_path, f"# {file_path}\n")
        return FileContent(
            file_name=file_path.split("/")[-1],
            file_path=file_path,
            size=len(content),
            encoding="base64",
            content=base64.b64encode(content.encode()).decode(),
            ref=ref,
        )

    @staticmethod
    def update_file(
        project_id: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
    ) -> CommitResult:
        return CommitResult(
            id="demo_commit_abc123",
            short_id="abc123",
            title=commit_message,
            message=commit_message,
        )

    @staticmethod
    def create_branch(project_id: str, branch_name: str, ref: str = "main") -> BranchInfo:
        return BranchInfo(
            name=branch_name,
            protected=False,
            commit_sha="demo_sha_abc123",
        )

    # ─── Commit Responses ──────────────────────────────────────────────────

    @staticmethod
    def create_commit(
        project_id: str,
        branch: str,
        message: str,
        actions: list,
    ) -> CommitResult:
        return CommitResult(
            id="demo_batch_commit_def456",
            short_id="def456",
            title=message,
            message=message,
            stats={"additions": len(actions), "deletions": 0, "total": len(actions)},
        )

    # ─── Security Responses ────────────────────────────────────────────────

    @staticmethod
    def get_vulnerabilities(project_id: str) -> List[VulnerabilityInfo]:
        scenario = _load_scenario("security_vulnerability.json")
        return [
            VulnerabilityInfo(
                id=1,
                name="SQL Injection in user input handler",
                description="Unsanitized user input passed to SQL query",
                severity=VulnerabilitySeverity.CRITICAL,
                confidence="high",
                scanner="sast",
                solution="Use parameterized queries",
                state="detected",
            ),
            VulnerabilityInfo(
                id=2,
                name="Outdated dependency with known CVE",
                description="lodash < 4.17.21 has prototype pollution",
                severity=VulnerabilitySeverity.HIGH,
                confidence="medium",
                scanner="dependency_scanning",
                solution="Upgrade lodash to >= 4.17.21",
                state="detected",
            ),
        ]

    @staticmethod
    def get_dependency_alerts(project_id: str) -> List[DependencyAlert]:
        return [
            DependencyAlert(
                dependency_name="lodash",
                dependency_version="4.17.19",
                vulnerability="Prototype Pollution",
                severity=VulnerabilitySeverity.HIGH,
                fixed_version="4.17.21",
                cve_id="CVE-2021-23337",
            ),
            DependencyAlert(
                dependency_name="requests",
                dependency_version="2.25.0",
                vulnerability="CRLF injection in HTTP headers",
                severity=VulnerabilitySeverity.MEDIUM,
                fixed_version="2.31.0",
                cve_id="CVE-2023-32681",
            ),
        ]
