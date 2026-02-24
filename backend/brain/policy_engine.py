"""
AutoForge Policy Engine — Governance, safety constraints, and guardrails.
"""

from typing import Tuple

from models.workflows import AgentTask, Workflow


class PolicyEngine:
    """
    Enforces safety policies and governance rules.

    Guardrails:
    - No destructive edits
    - No production config changes
    - Branch protection enforcement
    - Diff size limits
    - Approval gates for high-risk actions
    - Rate limiting
    """

    # Actions that require human approval
    HIGH_RISK_ACTIONS = {
        "delete_branch",
        "force_push",
        "modify_production_config",
        "update_secrets",
        "drop_database",
        "reset_hard",
    }

    # Protected branches — agents cannot directly push here
    PROTECTED_BRANCHES = {"main", "master", "production", "release", "staging"}

    # Maximum diff size (lines) an agent can submit in a single MR
    MAX_DIFF_LINES = 500

    # Maximum concurrent workflows per project
    MAX_CONCURRENT_WORKFLOWS = 5

    def check_policy(self, task: AgentTask, workflow: Workflow) -> Tuple[bool, str]:
        """
        Check if a task is allowed by governance policies.

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check for high-risk actions
        if task.action in self.HIGH_RISK_ACTIONS:
            return False, f"Action '{task.action}' requires human approval"

        # Branch protection: agents must create fix branches, never push to protected
        target_branch = task.input_data.get("target_branch", "")
        if target_branch in self.PROTECTED_BRANCHES and task.action in (
            "edit_file", "push_changes", "direct_commit",
        ):
            return False, f"Direct edits to protected branch '{target_branch}' are forbidden — use a merge request"

        # Diff size validation
        diff = task.input_data.get("diff", "")
        if diff and diff.count("\n") > self.MAX_DIFF_LINES:
            return False, f"Diff size ({diff.count(chr(10))} lines) exceeds limit ({self.MAX_DIFF_LINES})"

        # Check risk threshold
        from config import settings
        if task.risk_score > settings.AGENT_RISK_THRESHOLD:
            return False, f"Risk score {task.risk_score} exceeds threshold {settings.AGENT_RISK_THRESHOLD}"

        # Check confidence threshold
        if task.confidence > 0 and task.confidence < settings.AGENT_CONFIDENCE_THRESHOLD:
            return False, f"Confidence {task.confidence} below threshold {settings.AGENT_CONFIDENCE_THRESHOLD}"

        return True, "Policy check passed"

    def get_approval_requirements(self, task: AgentTask) -> dict:
        """Get approval requirements for a task."""
        if task.action in self.HIGH_RISK_ACTIONS:
            return {
                "requires_approval": True,
                "approval_type": "human",
                "reason": f"High-risk action: {task.action}",
            }

        if task.risk_score > 0.9:
            return {
                "requires_approval": True,
                "approval_type": "human",
                "reason": f"Very high risk score: {task.risk_score}",
            }

        target_branch = task.input_data.get("target_branch", "")
        if target_branch in self.PROTECTED_BRANCHES:
            return {
                "requires_approval": True,
                "approval_type": "branch_protection",
                "reason": f"Target branch '{target_branch}' is protected",
            }

        return {"requires_approval": False}
