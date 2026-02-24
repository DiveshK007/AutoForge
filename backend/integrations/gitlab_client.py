"""
AutoForge GitLab API Client — Programmatic access to GitLab.
"""

from typing import Any, Dict, List, Optional
import httpx

from config import settings


class GitLabClient:
    """
    GitLab REST API client for AutoForge operations.

    Handles:
    - Pipeline operations
    - Repository file operations
    - Merge request management
    - Branch management
    - Issue management
    """

    def __init__(self):
        self.base_url = settings.GITLAB_URL.rstrip("/")
        self.token = settings.GITLAB_API_TOKEN
        self.headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to GitLab API."""
        url = f"{self.base_url}/api/v4{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, headers=self.headers, **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    # ─── Pipeline Operations ───

    async def get_pipeline(self, project_id: str, pipeline_id: int) -> Dict:
        """Get pipeline details."""
        return await self._request("GET", f"/projects/{project_id}/pipelines/{pipeline_id}")

    async def get_pipeline_jobs(self, project_id: str, pipeline_id: int) -> List[Dict]:
        """Get jobs for a pipeline."""
        return await self._request("GET", f"/projects/{project_id}/pipelines/{pipeline_id}/jobs")

    async def get_job_log(self, project_id: str, job_id: int) -> str:
        """Get job trace/log."""
        url = f"{self.base_url}/api/v4/projects/{project_id}/jobs/{job_id}/trace"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text

    async def retry_pipeline(self, project_id: str, pipeline_id: int) -> Dict:
        """Retry a failed pipeline."""
        return await self._request("POST", f"/projects/{project_id}/pipelines/{pipeline_id}/retry")

    async def create_pipeline(self, project_id: str, ref: str = "main") -> Dict:
        """Create a new pipeline."""
        return await self._request(
            "POST",
            f"/projects/{project_id}/pipeline",
            json={"ref": ref},
        )

    # ─── Repository Operations ───

    async def get_file(self, project_id: str, file_path: str, ref: str = "main") -> Dict:
        """Get file content from repository."""
        import urllib.parse
        encoded_path = urllib.parse.quote(file_path, safe="")
        return await self._request(
            "GET",
            f"/projects/{project_id}/repository/files/{encoded_path}",
            params={"ref": ref},
        )

    async def create_or_update_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        action: str = "update",
    ) -> Dict:
        """Create or update a file in the repository."""
        import urllib.parse
        encoded_path = urllib.parse.quote(file_path, safe="")
        method = "PUT" if action == "update" else "POST"

        return await self._request(
            method,
            f"/projects/{project_id}/repository/files/{encoded_path}",
            json={
                "branch": branch,
                "content": content,
                "commit_message": commit_message,
            },
        )

    async def get_repository_tree(
        self, project_id: str, path: str = "", ref: str = "main"
    ) -> List[Dict]:
        """Get repository file tree."""
        return await self._request(
            "GET",
            f"/projects/{project_id}/repository/tree",
            params={"path": path, "ref": ref},
        )

    # ─── Branch Operations ───

    async def create_branch(
        self, project_id: str, branch: str, ref: str = "main"
    ) -> Dict:
        """Create a new branch."""
        return await self._request(
            "POST",
            f"/projects/{project_id}/repository/branches",
            json={"branch": branch, "ref": ref},
        )

    async def delete_branch(self, project_id: str, branch: str) -> Dict:
        """Delete a branch."""
        import urllib.parse
        encoded = urllib.parse.quote(branch, safe="")
        return await self._request(
            "DELETE",
            f"/projects/{project_id}/repository/branches/{encoded}",
        )

    # ─── Merge Request Operations ───

    async def create_merge_request(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
        labels: str = "autoforge",
    ) -> Dict:
        """Create a merge request."""
        return await self._request(
            "POST",
            f"/projects/{project_id}/merge_requests",
            json={
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
                "labels": labels,
                "remove_source_branch": True,
            },
        )

    async def get_merge_request(self, project_id: str, mr_iid: int) -> Dict:
        """Get merge request details."""
        return await self._request("GET", f"/projects/{project_id}/merge_requests/{mr_iid}")

    async def get_merge_request_changes(self, project_id: str, mr_iid: int) -> Dict:
        """Get merge request diff/changes."""
        return await self._request("GET", f"/projects/{project_id}/merge_requests/{mr_iid}/changes")

    async def comment_on_merge_request(
        self, project_id: str, mr_iid: int, body: str
    ) -> Dict:
        """Add a note/comment to a merge request."""
        return await self._request(
            "POST",
            f"/projects/{project_id}/merge_requests/{mr_iid}/notes",
            json={"body": body},
        )

    # ─── Issue Operations ───

    async def create_issue(
        self, project_id: str, title: str, description: str = "", labels: str = "autoforge"
    ) -> Dict:
        """Create an issue."""
        return await self._request(
            "POST",
            f"/projects/{project_id}/issues",
            json={
                "title": title,
                "description": description,
                "labels": labels,
            },
        )

    # ─── Project Operations ───

    async def get_project(self, project_id: str) -> Dict:
        """Get project details."""
        return await self._request("GET", f"/projects/{project_id}")

    async def get_vulnerabilities(self, project_id: str) -> List[Dict]:
        """Get project vulnerabilities."""
        return await self._request("GET", f"/projects/{project_id}/vulnerability_findings")
