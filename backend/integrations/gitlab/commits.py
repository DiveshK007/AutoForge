"""
AutoForge GitLab Integration — Commit service.

Provides batch-commit (multi-file) support for agents that need to
modify several files in a single atomic commit.
"""

import logging
from typing import List, Optional

from config import settings
from integrations.gitlab.auth import is_forbidden_path
from integrations.gitlab.gitlab_client import GitLabAPIClient
from integrations.gitlab.demo_mode import DemoModeSimulator
from integrations.gitlab.models import CommitAction, CommitResult

logger = logging.getLogger("autoforge.integrations.gitlab.commits")

PROTECTED_BRANCHES = frozenset({"main", "master", "production", "release", "staging"})


class CommitService:
    """Atomic multi-file commit operations."""

    def __init__(self, client: Optional[GitLabAPIClient] = None) -> None:
        self._client = client or GitLabAPIClient()

    async def create_commit(
        self,
        project_id: str,
        branch: str,
        message: str,
        actions: List[CommitAction],
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> CommitResult:
        """
        Create an atomic commit containing multiple file changes.

        Args:
            project_id: GitLab project ID.
            branch: Target branch (must not be protected).
            message: Commit message.
            actions: List of file actions to include.

        Returns:
            CommitResult with the new commit SHA.

        Raises:
            PermissionError: If branch is protected or path is forbidden.
            ValueError: If actions list is empty.
        """
        if not actions:
            raise ValueError("At least one commit action is required")

        if branch in PROTECTED_BRANCHES:
            raise PermissionError(f"Cannot commit directly to protected branch '{branch}'")

        # Validate every file path
        for action in actions:
            if is_forbidden_path(action.file_path):
                raise PermissionError(f"Commit blocked — forbidden path: {action.file_path}")

        if settings.DEMO_MODE:
            return DemoModeSimulator.create_commit(
                project_id, branch, message, [a.model_dump() for a in actions],
            )

        payload = {
            "branch": branch,
            "commit_message": message,
            "actions": [
                {
                    "action": a.action,
                    "file_path": a.file_path,
                    "content": a.content,
                    **({"previous_path": a.previous_path} if a.previous_path else {}),
                    "encoding": a.encoding,
                }
                for a in actions
            ],
        }

        data = await self._client.post(
            f"/projects/{project_id}/repository/commits",
            payload=payload,
            agent=agent, workflow_id=workflow_id,
        )

        return CommitResult(
            id=data.get("id", ""),
            short_id=data.get("short_id", ""),
            title=data.get("title", message),
            message=data.get("message", message),
            author_name=data.get("author_name", "AutoForge"),
            web_url=data.get("web_url"),
            stats=data.get("stats", {}),
        )
