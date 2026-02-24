"""
AutoForge GitLab Integration — Pipeline service.

Encapsulates all CI/CD pipeline interactions.  Every method returns typed
Pydantic models, supports DEMO_MODE, and emits telemetry.
"""

import logging
from typing import List, Optional

from config import settings
from integrations.gitlab.gitlab_client import GitLabAPIClient
from integrations.gitlab.demo_mode import DemoModeSimulator
from integrations.gitlab.models import PipelineInfo, JobInfo

logger = logging.getLogger("autoforge.integrations.gitlab.pipelines")


class PipelineService:
    """CI/CD pipeline operations."""

    def __init__(self, client: Optional[GitLabAPIClient] = None) -> None:
        self._client = client or GitLabAPIClient()

    async def get_pipeline(
        self, project_id: str, pipeline_id: int, *, agent: str = None, workflow_id: str = None
    ) -> PipelineInfo:
        """Retrieve pipeline metadata."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.get_pipeline(project_id, pipeline_id)

        data = await self._client.get(
            f"/projects/{project_id}/pipelines/{pipeline_id}",
            agent=agent, workflow_id=workflow_id,
        )
        return PipelineInfo(**data)

    async def get_pipeline_jobs(
        self, project_id: str, pipeline_id: int, *, agent: str = None, workflow_id: str = None
    ) -> List[JobInfo]:
        """List all jobs for a pipeline."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.get_pipeline_jobs(project_id, pipeline_id)

        data = await self._client.get(
            f"/projects/{project_id}/pipelines/{pipeline_id}/jobs",
            agent=agent, workflow_id=workflow_id,
        )
        return [JobInfo(**j) for j in data] if isinstance(data, list) else []

    async def get_failed_jobs(
        self, project_id: str, pipeline_id: int, *, agent: str = None, workflow_id: str = None
    ) -> List[JobInfo]:
        """Convenience: return only failed jobs."""
        jobs = await self.get_pipeline_jobs(project_id, pipeline_id, agent=agent, workflow_id=workflow_id)
        return [j for j in jobs if j.status == "failed"]

    async def get_job_log(
        self, project_id: str, job_id: int, *, tail: int = 5000, agent: str = None, workflow_id: str = None
    ) -> str:
        """Get job trace / log text (last ``tail`` characters)."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.get_job_log(project_id, job_id)

        raw = await self._client.get_raw(
            f"/projects/{project_id}/jobs/{job_id}/trace",
            agent=agent, workflow_id=workflow_id,
        )
        return raw[-tail:] if len(raw) > tail else raw

    async def retry_pipeline(
        self, project_id: str, pipeline_id: int, *, agent: str = None, workflow_id: str = None
    ) -> PipelineInfo:
        """Retry a failed pipeline."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.retry_pipeline(project_id, pipeline_id)

        data = await self._client.post(
            f"/projects/{project_id}/pipelines/{pipeline_id}/retry",
            agent=agent, workflow_id=workflow_id,
        )
        return PipelineInfo(**data)

    async def trigger_pipeline(
        self, project_id: str, ref: str = "main", *, agent: str = None, workflow_id: str = None
    ) -> PipelineInfo:
        """Create (trigger) a new pipeline run."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.trigger_pipeline(project_id, ref)

        data = await self._client.post(
            f"/projects/{project_id}/pipeline",
            payload={"ref": ref},
            agent=agent, workflow_id=workflow_id,
        )
        return PipelineInfo(**data)
