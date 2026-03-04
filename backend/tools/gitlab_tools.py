"""
AutoForge GitLab Tools — Tool abstraction layer for agent execution.

Provides a clean tool interface for agents to interact with GitLab,
abstracting away API details and providing error handling.

This module is a **thin compatibility shim** — it delegates to the
enterprise ``ToolGateway`` which in turn routes through the typed
GitLab integration layer.
"""

from typing import Any, Dict, Optional

from tools.tool_gateway import ToolGateway


class GitLabTools:
    """
    Tool gateway for GitLab operations.

    Agents call these tools to execute actions on GitLab:
    - edit_file()
    - create_branch()
    - create_merge_request()
    - rerun_pipeline()
    - comment_on_mr()
    """

    def __init__(self):
        self._gw = ToolGateway()

    async def create_branch(
        self, project_id: str, branch: str, ref: str = "main"
    ) -> Dict[str, Any]:
        """Create a new branch for fixes."""
        result = await self._gw.create_branch(project_id, branch, ref)
        return result.to_dict()

    async def edit_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
    ) -> Dict[str, Any]:
        """Edit a file in the repository."""
        result = await self._gw.edit_file(project_id, file_path, content, branch, commit_message)
        return result.to_dict()

    async def create_merge_request(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a merge request."""
        result = await self._gw.create_merge_request(
            project_id, source_branch, target_branch, title, description,
        )
        return result.to_dict()

    async def rerun_pipeline(
        self, project_id: str, pipeline_id: Optional[int] = None, ref: str = "main"
    ) -> Dict[str, Any]:
        """Rerun a pipeline."""
        result = await self._gw.rerun_pipeline(project_id, pipeline_id, ref)
        return result.to_dict()

    async def comment_on_mr(
        self, project_id: str, mr_iid: int, body: str
    ) -> Dict[str, Any]:
        """Post a comment on a merge request."""
        result = await self._gw.comment_on_mr(project_id, mr_iid, body)
        return result.to_dict()

    async def get_file_content(
        self, project_id: str, file_path: str, ref: str = "main"
    ) -> Dict[str, Any]:
        """Get file content from repository."""
        result = await self._gw.get_file_content(project_id, file_path, ref)
        return result.to_dict()

    async def get_pipeline_logs(
        self, project_id: str, pipeline_id: int
    ) -> Dict[str, Any]:
        """Get logs from a pipeline's failed jobs."""
        result = await self._gw.get_pipeline_logs(project_id, pipeline_id)
        return result.to_dict()

    async def generate_tests(
        self,
        project_id: str,
        test_files: list,
        branch: str,
        commit_message: str = "test: add automated tests by AutoForge QA Agent",
    ) -> Dict[str, Any]:
        """Generate and commit test files to a branch."""
        result = await self._gw.generate_tests(project_id, test_files, branch, commit_message)
        return result.to_dict()

    async def update_docs(
        self,
        project_id: str,
        doc_files: list,
        branch: str,
        commit_message: str = "docs: update documentation by AutoForge Docs Agent",
    ) -> Dict[str, Any]:
        """Update documentation files on a branch."""
        result = await self._gw.update_docs(project_id, doc_files, branch, commit_message)
        return result.to_dict()
