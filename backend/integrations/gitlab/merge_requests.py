"""
AutoForge GitLab Integration — Merge Request service.

Create, comment, approve, and inspect merge requests.
"""

import logging
from typing import Any, Dict, Optional

from config import settings
from integrations.gitlab.gitlab_client import GitLabAPIClient
from integrations.gitlab.demo_mode import DemoModeSimulator
from integrations.gitlab.models import MergeRequestInfo, DiffInfo

logger = logging.getLogger("autoforge.integrations.gitlab.merge_requests")


class MergeRequestService:
    """Merge request automation."""

    def __init__(self, client: Optional[GitLabAPIClient] = None) -> None:
        self._client = client or GitLabAPIClient()

    async def create(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
        labels: str = "autoforge",
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> MergeRequestInfo:
        """Open a new merge request."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.create_merge_request(
                project_id, source_branch, target_branch, title, description,
            )

        data = await self._client.post(
            f"/projects/{project_id}/merge_requests",
            payload={
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
                "labels": labels,
                "remove_source_branch": True,
            },
            agent=agent, workflow_id=workflow_id,
        )
        return MergeRequestInfo(**data)

    async def comment(
        self,
        project_id: str,
        mr_iid: int,
        body: str,
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> Dict[str, Any]:
        """Post a note / comment on a merge request."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.comment_on_mr(project_id, mr_iid, body)

        return await self._client.post(
            f"/projects/{project_id}/merge_requests/{mr_iid}/notes",
            payload={"body": body},
            agent=agent, workflow_id=workflow_id,
        )

    async def approve(
        self,
        project_id: str,
        mr_iid: int,
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> Dict[str, Any]:
        """Approve a merge request."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.approve_mr(project_id, mr_iid)

        return await self._client.post(
            f"/projects/{project_id}/merge_requests/{mr_iid}/approve",
            agent=agent, workflow_id=workflow_id,
        )

    async def get_changes(
        self,
        project_id: str,
        mr_iid: int,
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> MergeRequestInfo:
        """Get merge request metadata + diff list."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.get_mr_changes(project_id, mr_iid)

        data = await self._client.get(
            f"/projects/{project_id}/merge_requests/{mr_iid}/changes",
            agent=agent, workflow_id=workflow_id,
        )
        changes = [DiffInfo(**c) for c in data.get("changes", [])]
        mr = MergeRequestInfo(
            id=data.get("id", 0),
            iid=data.get("iid", mr_iid),
            project_id=data.get("project_id", int(project_id) if project_id.isdigit() else 0),
            title=data.get("title", ""),
            state=data.get("state", "opened"),
            source_branch=data.get("source_branch", ""),
            target_branch=data.get("target_branch", "main"),
            changes=changes,
            has_conflicts=data.get("has_conflicts", False),
        )
        return mr

    async def get_merge_request(
        self,
        project_id: str,
        mr_iid: int,
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> MergeRequestInfo:
        """Get merge request by IID."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.get_mr_changes(project_id, mr_iid)

        data = await self._client.get(
            f"/projects/{project_id}/merge_requests/{mr_iid}",
            agent=agent, workflow_id=workflow_id,
        )
        return MergeRequestInfo(**data)
