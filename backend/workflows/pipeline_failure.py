"""
AutoForge Pipeline Failure Workflow — Primary autonomous remediation flow.

This is the flagship workflow that demonstrates:
1. Event detection
2. Multi-agent orchestration
3. Autonomous diagnosis
4. Fix generation
5. PR creation
6. Test generation
7. Documentation update
8. Sustainability analysis
"""


from models.events import NormalizedEvent, EventType


class PipelineFailureWorkflow:
    """
    Orchestrates the complete pipeline failure remediation cycle.

    Flow:
    Trigger → Brain → SRE Diagnose → Security Validate → QA Test →
    Docs Update → GreenOps Analyze → PR Created → Learning Encoded
    """

    WORKFLOW_STEPS = [
        {
            "agent": "sre",
            "action": "diagnose_and_fix",
            "description": "Diagnose pipeline failure and generate fix",
            "critical": True,
        },
        {
            "agent": "security",
            "action": "validate_fix_security",
            "description": "Validate fix doesn't introduce vulnerabilities",
            "critical": False,
        },
        {
            "agent": "qa",
            "action": "generate_tests",
            "description": "Generate tests for the fix",
            "critical": False,
        },
        {
            "agent": "docs",
            "action": "update_changelog",
            "description": "Update changelog with fix details",
            "critical": False,
        },
        {
            "agent": "greenops",
            "action": "analyze_efficiency",
            "description": "Analyze pipeline sustainability",
            "critical": False,
        },
    ]

    @staticmethod
    def matches(event: NormalizedEvent) -> bool:
        """Check if this workflow handles the given event."""
        return event.event_type == EventType.PIPELINE_FAILURE

    def get_steps(self) -> list:
        """Get the ordered list of workflow steps."""
        return self.WORKFLOW_STEPS
