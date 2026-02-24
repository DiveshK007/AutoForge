"""
AutoForge Agent Router — Maps events to appropriate agents.
"""

from typing import Dict, List

from models.events import EventType


# Event → Agent routing table
EVENT_AGENT_MAP: Dict[str, List[str]] = {
    EventType.PIPELINE_FAILURE.value: ["sre", "security", "qa", "docs", "greenops"],
    EventType.MERGE_REQUEST_OPENED.value: ["review", "security", "qa"],
    EventType.MERGE_REQUEST_UPDATED.value: ["review"],
    EventType.MERGE_REQUEST_MERGED.value: ["docs", "greenops"],
    EventType.SECURITY_ALERT.value: ["security", "sre", "qa"],
    EventType.DEPENDENCY_ALERT.value: ["security", "qa"],
    EventType.PUSH.value: ["review"],
    EventType.PIPELINE_SUCCESS.value: ["greenops"],
    EventType.MANUAL_TRIGGER.value: ["sre"],
}

# Agent action mapping per event
EVENT_ACTION_MAP: Dict[str, Dict[str, str]] = {
    EventType.PIPELINE_FAILURE.value: {
        "sre": "diagnose_and_fix",
        "security": "validate_fix_security",
        "qa": "generate_tests",
        "docs": "update_changelog",
        "greenops": "analyze_efficiency",
    },
    EventType.MERGE_REQUEST_OPENED.value: {
        "review": "review_code",
        "security": "scan_changes",
        "qa": "suggest_tests",
    },
    EventType.MERGE_REQUEST_MERGED.value: {
        "docs": "update_documentation",
        "greenops": "post_merge_analysis",
    },
    EventType.SECURITY_ALERT.value: {
        "security": "analyze_and_patch",
        "sre": "assess_impact",
        "qa": "regression_check",
    },
    EventType.DEPENDENCY_ALERT.value: {
        "security": "patch_dependency",
        "qa": "validate_patch",
    },
}


class AgentRouter:
    """Routes events to appropriate agents based on event type."""

    def get_agents_for_event(self, event_type: str) -> List[str]:
        """Get list of agent types that should handle this event."""
        return EVENT_AGENT_MAP.get(event_type, ["sre"])

    def get_action_for_agent(self, event_type: str, agent_type: str) -> str:
        """Get the specific action an agent should perform for an event."""
        actions = EVENT_ACTION_MAP.get(event_type, {})
        return actions.get(agent_type, "analyze")

    def get_agent_priority(self, event_type: str, agent_type: str) -> int:
        """
        Get execution priority for an agent.
        Lower number = higher priority = runs first.
        """
        priority_order = EVENT_AGENT_MAP.get(event_type, [])
        try:
            return priority_order.index(agent_type)
        except ValueError:
            return 99
