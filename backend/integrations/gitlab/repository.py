"""
AutoForge GitLab Integration — Repository service.

File read/write, branch creation, and tree listing.  Every write
operation is guarded by the auth module's forbidden-path check.
"""

import logging
import urllib.parse
from typing import List, Optional

from config import settings
from integrations.gitlab.auth import is_forbidden_path
from integrations.gitlab.gitlab_client import GitLabAPIClient
from integrations.gitlab.demo_mode import DemoModeSimulator
from integrations.gitlab.models import FileContent, BranchInfo, CommitResult

logger = logging.getLogger("autoforge.integrations.gitlab.repository")

# Protected branches that agents must never push to directly
PROTECTED_BRANCHES = frozenset({"main", "master", "production", "release", "staging"})


class RepositoryService:
    """Git repository file and branch operations."""

    def __init__(self, client: Optional[GitLabAPIClient] = None) -> None:
        self._client = client or GitLabAPIClient()

    # ─── Read ──────────────────────────────────────────────────────────────

    async def get_file(
        self, project_id: str, file_path: str, ref: str = "main",
        *, agent: str = None, workflow_id: str = None,
    ) -> FileContent:
        """Read a single file from the repository."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.get_file(project_id, file_path, ref)

        encoded = urllib.parse.quote(file_path, safe="")
        data = await self._client.get(
            f"/projects/{project_id}/repository/files/{encoded}",
            params={"ref": ref},
            agent=agent, workflow_id=workflow_id,
        )
        return FileContent(**data)

    async def get_tree(
        self, project_id: str, path: str = "", ref: str = "main",
        *, agent: str = None, workflow_id: str = None,
    ) -> List[dict]:
        """List repository tree."""
        if settings.DEMO_MODE:
            return [
                {"name": "requirements.txt", "type": "blob", "path": "requirements.txt"},
                {"name": "src", "type": "tree", "path": "src"},
                {"name": "tests", "type": "tree", "path": "tests"},
            ]

        data = await self._client.get(
            f"/projects/{project_id}/repository/tree",
            params={"path": path, "ref": ref, "per_page": 100},
            agent=agent, workflow_id=workflow_id,
        )
        return data if isinstance(data, list) else []

    # ─── Write ─────────────────────────────────────────────────────────────

    async def update_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> CommitResult:
        """Update an existing file on a branch.  Blocks forbidden paths."""
        self._guard_write(file_path, branch)

        if settings.DEMO_MODE:
            return DemoModeSimulator.update_file(project_id, file_path, content, branch, commit_message)

        encoded = urllib.parse.quote(file_path, safe="")
        data = await self._client.put(
            f"/projects/{project_id}/repository/files/{encoded}",
            payload={"branch": branch, "content": content, "commit_message": commit_message},
            agent=agent, workflow_id=workflow_id,
        )
        return CommitResult(id=data.get("commit_id", ""), title=commit_message, message=commit_message)

    async def create_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> CommitResult:
        """Create a new file on a branch."""
        self._guard_write(file_path, branch)

        if settings.DEMO_MODE:
            return DemoModeSimulator.update_file(project_id, file_path, content, branch, commit_message)

        encoded = urllib.parse.quote(file_path, safe="")
        data = await self._client.post(
            f"/projects/{project_id}/repository/files/{encoded}",
            payload={"branch": branch, "content": content, "commit_message": commit_message},
            agent=agent, workflow_id=workflow_id,
        )
        return CommitResult(id=data.get("commit_id", ""), title=commit_message, message=commit_message)

    # ─── Branch ────────────────────────────────────────────────────────────

    async def create_branch(
        self, project_id: str, branch_name: str, ref: str = "main",
        *, agent: str = None, workflow_id: str = None,
    ) -> BranchInfo:
        """Create a new branch.  The branch name itself must not be protected."""
        if branch_name in PROTECTED_BRANCHES:
            raise ValueError(f"Cannot create branch with protected name '{branch_name}'")

        if settings.DEMO_MODE:
            return DemoModeSimulator.create_branch(project_id, branch_name, ref)

        data = await self._client.post(
            f"/projects/{project_id}/repository/branches",
            payload={"branch": branch_name, "ref": ref},
            agent=agent, workflow_id=workflow_id,
        )
        return BranchInfo(
            name=data.get("name", branch_name),
            protected=data.get("protected", False),
            commit_sha=data.get("commit", {}).get("id"),
        )

    async def delete_branch(
        self, project_id: str, branch_name: str,
        *, agent: str = None, workflow_id: str = None,
    ) -> bool:
        """Delete a branch.  Protected branches cannot be deleted."""
        if branch_name in PROTECTED_BRANCHES:
            raise ValueError(f"Cannot delete protected branch '{branch_name}'")

        if settings.DEMO_MODE:
            return True

        encoded = urllib.parse.quote(branch_name, safe="")
        await self._client.delete(
            f"/projects/{project_id}/repository/branches/{encoded}",
            agent=agent, workflow_id=workflow_id,
        )
        return True

    # ─── Guards ────────────────────────────────────────────────────────────

    @staticmethod
    def _guard_write(file_path: str, branch: str) -> None:
        """Raise if the write targets a forbidden path or protected branch."""
        if is_forbidden_path(file_path):
            raise PermissionError(f"Write to forbidden path blocked: {file_path}")
        if branch in PROTECTED_BRANCHES:
            raise PermissionError(f"Direct write to protected branch '{branch}' is forbidden — use a feature branch")
