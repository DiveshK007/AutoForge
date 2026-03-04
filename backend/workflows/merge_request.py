"""
AutoForge Merge Request Workflow — Autonomous code review & validation.

This workflow handles:
1. Automated code review
2. Security scanning of changes
3. Test generation for new code
4. Documentation generation
5. Performance / sustainability assessment
"""


from models.events import NormalizedEvent, EventType


class MergeRequestWorkflow:
    """
    Orchestrates the complete merge request review cycle.

    Flow:
    Trigger → Brain → Review Analysis → Security Scan → QA Tests →
    Docs Update → GreenOps Assessment → Ready to Merge
    """

    WORKFLOW_STEPS = [
        {
            "agent": "review",
            "action": "review_merge_request",
            "description": "Automated code review: architecture, patterns, quality",
            "critical": True,
        },
        {
            "agent": "security",
            "action": "scan_changes",
            "description": "Security scan of MR diff for vulnerabilities",
            "critical": True,
        },
        {
            "agent": "qa",
            "action": "generate_tests",
            "description": "Generate missing test coverage for new code paths",
            "critical": False,
            "depends_on": ["review"],
        },
        {
            "agent": "sre",
            "action": "validate_infrastructure",
            "description": "Check for infrastructure config changes and validate",
            "critical": False,
            "depends_on": ["review"],
        },
        {
            "agent": "docs",
            "action": "update_documentation",
            "description": "Update API docs and README for public-facing changes",
            "critical": False,
            "depends_on": ["review", "qa"],
        },
        {
            "agent": "greenops",
            "action": "analyze_efficiency",
            "description": "Estimate CI/CD energy cost of the merge",
            "critical": False,
        },
    ]

    @staticmethod
    def matches(event: NormalizedEvent) -> bool:
        """Check if this workflow handles the given event."""
        return event.event_type in (
            EventType.MERGE_REQUEST_OPENED,
            EventType.MERGE_REQUEST_UPDATED,
        )

    def get_steps(self) -> list:
        """Get the ordered list of workflow steps."""
        return self.WORKFLOW_STEPS
