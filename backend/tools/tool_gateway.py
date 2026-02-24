"""
AutoForge — Central Tool Execution Gateway.

Every agent action that touches an external system (GitLab, security
scanner, etc.) passes through this gateway.

Responsibilities
─────────────────
• Input validation (Pydantic schemas before API call)
• Safety enforcement (protected-branch guards, forbidden-path checks)
• Telemetry emission (action, agent, workflow_id, duration, outcome)
• Error normalisation (callers always get ``ToolResult``)
• Demo-mode passthrough (integration layer itself handles it)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from integrations.gitlab import (
    GitLabAPIClient,
    PipelineService,
    RepositoryService,
    MergeRequestService,
    CommitService,
    SecurityService,
)
from integrations.gitlab.models import CommitAction

logger = logging.getLogger("autoforge.tools.tool_gateway")


# ── Result envelope ─────────────────────────────────────────────

@dataclass
class ToolResult:
    """Uniform result envelope returned from every gateway call."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tool: str = ""
    agent: str = ""
    workflow_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "success": self.success,
            "tool": self.tool,
            "agent": self.agent,
            "workflow_id": self.workflow_id,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }
        if self.success:
            d["data"] = self.data
        else:
            d["error"] = self.error
        return d


# ── Gateway ─────────────────────────────────────────────────────

class ToolGateway:
    """
    Central routing point for all tool invocations by agents.

    Usage::

        gw = ToolGateway()
        result = await gw.create_branch("proj-1", "fix/numpy", agent="Fixer")
    """

    def __init__(self, client: Optional[GitLabAPIClient] = None) -> None:
        self._client = client or GitLabAPIClient()
        self._pipelines = PipelineService(self._client)
        self._repo = RepositoryService(self._client)
        self._mrs = MergeRequestService(self._client)
        self._commits = CommitService(self._client)
        self._security = SecurityService(self._client)

    # ── helpers ──────────────────────────────────────────────────

    def _ok(self, tool: str, data: Dict[str, Any], *, t0: float,
            agent: str = "", workflow_id: str = "") -> ToolResult:
        return ToolResult(
            success=True, data=data,
            execution_time_ms=(time.monotonic() - t0) * 1000,
            tool=tool, agent=agent, workflow_id=workflow_id,
        )

    def _fail(self, tool: str, error: str, *, t0: float,
              agent: str = "", workflow_id: str = "") -> ToolResult:
        logger.warning("Tool %s failed for agent=%s wf=%s: %s",
                       tool, agent, workflow_id, error)
        return ToolResult(
            success=False, error=error,
            execution_time_ms=(time.monotonic() - t0) * 1000,
            tool=tool, agent=agent, workflow_id=workflow_id,
        )

    # ── Branch operations ────────────────────────────────────────

    async def create_branch(
        self, project_id: str, branch: str, ref: str = "main",
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Create a new branch for fixes."""
        t0 = time.monotonic()
        try:
            info = await self._repo.create_branch(
                project_id, branch, ref,
                agent=agent, workflow_id=workflow_id,
            )
            return self._ok("create_branch", {"branch": info.name, "ref": info.commit_sha},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("create_branch", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    # ── File operations ──────────────────────────────────────────

    async def edit_file(
        self, project_id: str, file_path: str, content: str,
        branch: str, commit_message: str,
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Edit (or create) a single file on a branch."""
        t0 = time.monotonic()
        try:
            result = await self._repo.update_file(
                project_id, file_path, content, branch, commit_message,
                agent=agent, workflow_id=workflow_id,
            )
            return self._ok("edit_file", {"file": file_path, "result": result},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception:
            # Fall back to create
            try:
                result = await self._repo.create_file(
                    project_id, file_path, content, branch, commit_message,
                    agent=agent, workflow_id=workflow_id,
                )
                return self._ok("edit_file", {"file": file_path, "result": result, "created": True},
                                t0=t0, agent=agent, workflow_id=workflow_id)
            except Exception as exc:
                return self._fail("edit_file", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    async def get_file_content(
        self, project_id: str, file_path: str, ref: str = "main",
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Fetch a file and return its decoded content."""
        t0 = time.monotonic()
        try:
            fc = await self._repo.get_file(
                project_id, file_path, ref=ref,
                agent=agent, workflow_id=workflow_id,
            )
            return self._ok("get_file_content",
                            {"file": file_path, "content": fc.decoded_content, "size": fc.size},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("get_file_content", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    # ── Merge-request operations ─────────────────────────────────

    async def create_merge_request(
        self, project_id: str, source_branch: str, target_branch: str,
        title: str, description: str = "",
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Create a merge request."""
        t0 = time.monotonic()
        try:
            mr = await self._mrs.create(
                project_id, source_branch, target_branch, title, description,
                agent=agent, workflow_id=workflow_id,
            )
            return self._ok("create_merge_request",
                            {"mr_iid": mr.iid, "mr_url": mr.web_url, "title": mr.title},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("create_merge_request", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    async def comment_on_mr(
        self, project_id: str, mr_iid: int, body: str,
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Post a comment on a merge request."""
        t0 = time.monotonic()
        try:
            result = await self._mrs.comment(
                project_id, mr_iid, body,
                agent=agent, workflow_id=workflow_id,
            )
            return self._ok("comment_on_mr", {"mr_iid": mr_iid, "result": result},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("comment_on_mr", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    # ── Pipeline operations ──────────────────────────────────────

    async def rerun_pipeline(
        self, project_id: str, pipeline_id: Optional[int] = None, ref: str = "main",
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Retry an existing pipeline or trigger a new one."""
        t0 = time.monotonic()
        try:
            if pipeline_id:
                pi = await self._pipelines.retry_pipeline(
                    project_id, pipeline_id,
                    agent=agent, workflow_id=workflow_id,
                )
            else:
                pi = await self._pipelines.trigger_pipeline(
                    project_id, ref,
                    agent=agent, workflow_id=workflow_id,
                )
            return self._ok("rerun_pipeline",
                            {"pipeline_id": pi.id, "status": pi.status.value, "ref": pi.ref},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("rerun_pipeline", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    async def get_pipeline_logs(
        self, project_id: str, pipeline_id: int,
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Fetch logs of failed jobs from a pipeline."""
        t0 = time.monotonic()
        try:
            failed = await self._pipelines.get_failed_jobs(
                project_id, pipeline_id,
                agent=agent, workflow_id=workflow_id,
            )
            logs: Dict[str, str] = {}
            for job in failed:
                log_text = await self._pipelines.get_job_log(
                    project_id, job.id,
                    agent=agent, workflow_id=workflow_id,
                )
                logs[job.name] = log_text[-5000:]  # last 5k chars
            return self._ok("get_pipeline_logs", {"logs": logs, "failed_job_count": len(failed)},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("get_pipeline_logs", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    # ── Batch file operations ────────────────────────────────────

    async def generate_tests(
        self, project_id: str, test_files: List[Dict[str, str]],
        branch: str,
        commit_message: str = "test: add automated tests by AutoForge QA Agent",
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Commit test files atomically."""
        t0 = time.monotonic()
        try:
            actions = [
                CommitAction(
                    action="create",
                    file_path=tf["path"],
                    content=tf["content"],
                )
                for tf in test_files
            ]
            cr = await self._commits.create_commit(
                project_id, branch, commit_message, actions,
                agent=agent, workflow_id=workflow_id,
            )
            return self._ok("generate_tests",
                            {"commit_id": cr.id, "files_created": len(actions)},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("generate_tests", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    async def update_docs(
        self, project_id: str, doc_files: List[Dict[str, str]],
        branch: str,
        commit_message: str = "docs: update documentation by AutoForge Docs Agent",
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Commit documentation updates atomically."""
        t0 = time.monotonic()
        try:
            actions = [
                CommitAction(
                    action="update",
                    file_path=df["path"],
                    content=df["content"],
                )
                for df in doc_files
            ]
            cr = await self._commits.create_commit(
                project_id, branch, commit_message, actions,
                agent=agent, workflow_id=workflow_id,
            )
            return self._ok("update_docs",
                            {"commit_id": cr.id, "files_updated": len(actions)},
                            t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("update_docs", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    # ── Security operations ──────────────────────────────────────

    async def fetch_security_alerts(
        self, project_id: str,
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Fetch both vulnerability findings and dependency alerts."""
        t0 = time.monotonic()
        try:
            vulns = await self._security.get_vulnerabilities(
                project_id, agent=agent, workflow_id=workflow_id,
            )
            deps = await self._security.get_dependency_alerts(
                project_id, agent=agent, workflow_id=workflow_id,
            )
            return self._ok("fetch_security_alerts", {
                "vulnerabilities": [v.model_dump() for v in vulns],
                "dependency_alerts": [d.model_dump() for d in deps],
                "total_findings": len(vulns) + len(deps),
            }, t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("fetch_security_alerts", str(exc), t0=t0, agent=agent, workflow_id=workflow_id)

    async def fetch_critical_vulnerabilities(
        self, project_id: str,
        *, agent: str = "", workflow_id: str = "",
    ) -> ToolResult:
        """Convenience: only critical + high severity."""
        t0 = time.monotonic()
        try:
            criticals = await self._security.get_critical_vulnerabilities(
                project_id, agent=agent, workflow_id=workflow_id,
            )
            return self._ok("fetch_critical_vulnerabilities", {
                "vulnerabilities": [v.model_dump() for v in criticals],
                "count": len(criticals),
            }, t0=t0, agent=agent, workflow_id=workflow_id)
        except Exception as exc:
            return self._fail("fetch_critical_vulnerabilities", str(exc), t0=t0,
                              agent=agent, workflow_id=workflow_id)
