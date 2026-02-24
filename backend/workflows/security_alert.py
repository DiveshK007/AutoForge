"""
AutoForge Security Alert Workflow — Autonomous vulnerability remediation.

This workflow handles:
1. CVE detection and triage
2. Severity assessment
3. Patch generation
4. Security validation
5. Regression testing
6. Documentation
7. Sustainability analysis
"""

from typing import Any, Dict

from models.events import NormalizedEvent, EventType


class SecurityAlertWorkflow:
    """
    Orchestrates the complete security vulnerability remediation cycle.

    Flow:
    Trigger → Brain → Security Triage → SRE Patch → QA Regression →
    Review Validation → Docs Advisory → GreenOps Impact → Resolved
    """

    WORKFLOW_STEPS = [
        {
            "agent": "security",
            "action": "triage_vulnerability",
            "description": "Assess CVE severity, CVSS scoring, and blast radius",
            "critical": True,
        },
        {
            "agent": "sre",
            "action": "generate_patch",
            "description": "Generate dependency version bump or code patch",
            "critical": True,
            "depends_on": ["security"],
        },
        {
            "agent": "qa",
            "action": "regression_tests",
            "description": "Run regression tests to validate patch stability",
            "critical": False,
            "depends_on": ["sre"],
        },
        {
            "agent": "review",
            "action": "security_review",
            "description": "Verify patch does not introduce architectural issues",
            "critical": False,
            "depends_on": ["sre"],
        },
        {
            "agent": "docs",
            "action": "security_advisory",
            "description": "Generate security advisory and update CHANGELOG",
            "critical": False,
            "depends_on": ["review", "qa"],
        },
        {
            "agent": "greenops",
            "action": "analyze_efficiency",
            "description": "Assess CI/CD energy impact of remediation",
            "critical": False,
        },
    ]

    @staticmethod
    def matches(event: NormalizedEvent) -> bool:
        """Check if this workflow handles the given event."""
        return event.event_type in (
            EventType.SECURITY_ALERT,
            EventType.DEPENDENCY_ALERT,
        )

    def get_steps(self) -> list:
        """Get the ordered list of workflow steps."""
        return self.WORKFLOW_STEPS
