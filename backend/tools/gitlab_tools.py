"""
AutoForge GitLab Tools — Tool abstraction layer for agent execution.

Provides a clean tool interface for agents to interact with GitLab,
abstracting away API details and providing error handling.
"""

from typing import Any, Dict, Optional

from integrations.gitlab_client import GitLabClient


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
        self.client = GitLabClient()

    async def create_branch(
        self, project_id: str, branch: str, ref: str = "main"
    ) -> Dict[str, Any]:
        """Create a new branch for fixes."""
        try:
            result = await self.client.create_branch(project_id, branch, ref)
            return {"success": True, "branch": branch, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e), "branch": branch}

    async def edit_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
    ) -> Dict[str, Any]:
        """Edit a file in the repository."""
        try:
            result = await self.client.create_or_update_file(
                project_id, file_path, content, branch, commit_message
            )
            return {"success": True, "file": file_path, "result": result}
        except Exception as e:
            # Try creating the file if update fails
            try:
                result = await self.client.create_or_update_file(
                    project_id, file_path, content, branch, commit_message, action="create"
                )
                return {"success": True, "file": file_path, "result": result, "created": True}
            except Exception as e2:
                return {"success": False, "error": str(e2), "file": file_path}

    async def create_merge_request(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a merge request."""
        try:
            result = await self.client.create_merge_request(
                project_id, source_branch, target_branch, title, description
            )
            return {
                "success": True,
                "mr_iid": result.get("iid"),
                "mr_url": result.get("web_url"),
                "result": result,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def rerun_pipeline(
        self, project_id: str, pipeline_id: Optional[int] = None, ref: str = "main"
    ) -> Dict[str, Any]:
        """Rerun a pipeline."""
        try:
            if pipeline_id:
                result = await self.client.retry_pipeline(project_id, pipeline_id)
            else:
                result = await self.client.create_pipeline(project_id, ref)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def comment_on_mr(
        self, project_id: str, mr_iid: int, body: str
    ) -> Dict[str, Any]:
        """Post a comment on a merge request."""
        try:
            result = await self.client.comment_on_merge_request(
                project_id, mr_iid, body
            )
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_file_content(
        self, project_id: str, file_path: str, ref: str = "main"
    ) -> Dict[str, Any]:
        """Get file content from repository."""
        try:
            result = await self.client.get_file(project_id, file_path, ref)
            import base64
            content = base64.b64decode(result.get("content", "")).decode("utf-8")
            return {"success": True, "content": content, "file": file_path}
        except Exception as e:
            return {"success": False, "error": str(e), "file": file_path}

    async def get_pipeline_logs(
        self, project_id: str, pipeline_id: int
    ) -> Dict[str, Any]:
        """Get logs from a pipeline's failed jobs."""
        try:
            jobs = await self.client.get_pipeline_jobs(project_id, pipeline_id)
            logs = {}
            for job in jobs:
                if job.get("status") == "failed":
                    job_log = await self.client.get_job_log(project_id, job["id"])
                    logs[job["name"]] = job_log[-5000:]  # Last 5000 chars
            return {"success": True, "logs": logs}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def generate_tests(
        self,
        project_id: str,
        test_files: list,
        branch: str,
        commit_message: str = "test: add automated tests by AutoForge QA Agent",
    ) -> Dict[str, Any]:
        """Generate and commit test files to a branch."""
        results = []
        try:
            for test_file in test_files:
                result = await self.edit_file(
                    project_id,
                    test_file.get("path", ""),
                    test_file.get("content", ""),
                    branch,
                    commit_message,
                )
                results.append(result)
            return {"success": True, "files_created": len(results), "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_docs(
        self,
        project_id: str,
        doc_files: list,
        branch: str,
        commit_message: str = "docs: update documentation by AutoForge Docs Agent",
    ) -> Dict[str, Any]:
        """Update documentation files on a branch."""
        results = []
        try:
            for doc in doc_files:
                result = await self.edit_file(
                    project_id,
                    doc.get("path", ""),
                    doc.get("content", ""),
                    branch,
                    commit_message,
                )
                results.append(result)
            return {"success": True, "files_updated": len(results), "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
