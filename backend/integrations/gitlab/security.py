"""
AutoForge GitLab Integration — Security service.

Fetches vulnerability findings and dependency-scanning alerts.
"""

import logging
from typing import List, Optional

from config import settings
from integrations.gitlab.gitlab_client import GitLabAPIClient
from integrations.gitlab.demo_mode import DemoModeSimulator
from integrations.gitlab.models import VulnerabilityInfo, DependencyAlert

logger = logging.getLogger("autoforge.integrations.gitlab.security")


class SecurityService:
    """Security vulnerability and dependency alert operations."""

    def __init__(self, client: Optional[GitLabAPIClient] = None) -> None:
        self._client = client or GitLabAPIClient()

    async def get_vulnerabilities(
        self,
        project_id: str,
        *,
        severity: Optional[str] = None,
        agent: str = None,
        workflow_id: str = None,
    ) -> List[VulnerabilityInfo]:
        """
        Retrieve vulnerability findings for a project.

        Optionally filter by severity (critical, high, medium, low).
        """
        if settings.DEMO_MODE:
            vulns = DemoModeSimulator.get_vulnerabilities(project_id)
            if severity:
                vulns = [v for v in vulns if v.severity.value == severity.lower()]
            return vulns

        params = {"per_page": 100}
        if severity:
            params["severity"] = severity

        data = await self._client.get(
            f"/projects/{project_id}/vulnerability_findings",
            params=params,
            agent=agent, workflow_id=workflow_id,
        )
        return [VulnerabilityInfo(**v) for v in data] if isinstance(data, list) else []

    async def get_dependency_alerts(
        self,
        project_id: str,
        *,
        agent: str = None,
        workflow_id: str = None,
    ) -> List[DependencyAlert]:
        """Retrieve dependency-scanning alerts."""
        if settings.DEMO_MODE:
            return DemoModeSimulator.get_dependency_alerts(project_id)

        data = await self._client.get(
            f"/projects/{project_id}/dependencies",
            params={"per_page": 100},
            agent=agent, workflow_id=workflow_id,
        )

        alerts: List[DependencyAlert] = []
        if isinstance(data, list):
            for dep in data:
                for vuln in dep.get("vulnerabilities", []):
                    alerts.append(DependencyAlert(
                        dependency_name=dep.get("name", ""),
                        dependency_version=dep.get("version", ""),
                        vulnerability=vuln.get("name", ""),
                        severity=vuln.get("severity", "unknown"),
                        cve_id=vuln.get("identifiers", [{}])[0].get("value") if vuln.get("identifiers") else None,
                    ))
        return alerts

    async def get_critical_vulnerabilities(
        self, project_id: str, *, agent: str = None, workflow_id: str = None,
    ) -> List[VulnerabilityInfo]:
        """Convenience: critical + high severity only."""
        all_vulns = await self.get_vulnerabilities(project_id, agent=agent, workflow_id=workflow_id)
        return [v for v in all_vulns if v.severity.value in ("critical", "high")]
