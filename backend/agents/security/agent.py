"""
AutoForge Security Agent — DevSecOps Specialist.

Detects vulnerable dependencies, generates patches,
assesses exploit risk, and creates secure MRs.
Supports DEMO_MODE for deterministic reasoning.
"""

from typing import Any, Dict

from config import settings
from agents.base_agent import BaseAgent
from agents.reasoning_engine import ReasoningEngine
from models.workflows import AgentTask, Workflow


SECURITY_SYSTEM_PROMPT = """You are an elite Security Engineer AI operating inside GitLab as part of the AutoForge autonomous engineering organization.

Your responsibilities:
- Detect and analyze vulnerable dependencies
- Assess exploit severity and impact
- Generate secure patches with minimal breaking changes
- Verify patches don't introduce new vulnerabilities
- Score risk levels accurately

Guidelines:
- Always prioritize security over convenience
- Consider supply chain attack vectors
- Evaluate breaking change risk when patching
- Prefer pinned versions over ranges
- Document security rationale clearly"""


class SecurityAgent(BaseAgent):
    """
    Security Agent — DevSecOps Specialist.

    Handles:
    - CVE detection and analysis
    - Dependency vulnerability patching
    - Security code review
    - Risk scoring
    - Secure MR creation
    """

    def __init__(self):
        super().__init__(
            agent_type="security",
            capabilities=[
                "vulnerability_detection",
                "cve_analysis",
                "dependency_patching",
                "risk_scoring",
                "security_review",
            ],
        )
        self.reasoning_engine = ReasoningEngine()

    async def perceive(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Parse security context."""
        input_data = task.input_data

        context = {
            "vulnerability_id": input_data.get("vulnerability_id"),
            "severity": input_data.get("severity", "unknown"),
            "package": input_data.get("package"),
            "current_version": input_data.get("current_version"),
            "fixed_version": input_data.get("fixed_version"),
            "cve_id": input_data.get("cve_id"),
            "project_id": input_data.get("project_id"),
            "error_logs": input_data.get("error_logs", ""),
            "action": task.action,
        }

        # Consume shared context from upstream agents (e.g., SRE's fix)
        shared = input_data.get("_shared_context", {})
        if shared:
            context["upstream_analysis"] = shared
            sre_ctx = shared.get("sre", {})
            if sre_ctx:
                context["sre_fix_files"] = sre_ctx.get("files_modified", [])
                context["sre_root_cause"] = sre_ctx.get("root_cause", "")

        workflow.add_timeline_entry(
            "security_perception",
            agent="security",
            detail=f"Analyzing {context.get('severity', 'unknown')} severity issue: {context.get('cve_id', 'N/A')}",
        )

        return context

    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security threat and generate response plan."""
        action = context.get("action", "analyze_and_patch")

        if action == "validate_fix_security":
            return await self._reason_fix_validation(context, prior_knowledge)

        # ─── DEMO MODE ───
        if settings.DEMO_MODE:
            from demo.engine import get_demo_scenario
            scenario = get_demo_scenario("security_vulnerability") or {}
            hypotheses = scenario.get("hypotheses", [])
            confidence = scenario.get("confidence", 0.85)
            risk_score = scenario.get("risk_score", 0.15)
            return {
                "analysis": {"recommendation": scenario.get("root_cause", "Security patch required")},
                "confidence": confidence,
                "risk_score": risk_score,
                "severity": context.get("severity"),
                "patch_strategy": "update_dependency",
                "hypotheses": hypotheses,
            }

        reason_context = f"""Security Alert Analysis:

Vulnerability: {context.get('cve_id', 'Unknown CVE')}
Severity: {context.get('severity', 'unknown')}
Package: {context.get('package', 'unknown')}
Current Version: {context.get('current_version', 'unknown')}
Fixed Version: {context.get('fixed_version', 'unknown')}
Error Context: {context.get('error_logs', 'None')[:500]}

Prior knowledge: {prior_knowledge.get('similar_patches', 'None')}

Analyze:
1. What is the exploit risk?
2. Is the fixed version compatible?
3. What breaking changes might occur?
4. What is the recommended patch strategy?"""

        result = await self.reasoning_engine.reason(
            system_prompt=SECURITY_SYSTEM_PROMPT,
            context=reason_context,
            reasoning_framework="chain_of_thought",
            output_schema={
                "risk_level": "string (critical/high/medium/low)",
                "exploit_probability": "float 0-1",
                "patch_strategy": "string",
                "breaking_change_risk": "float 0-1",
                "confidence": "float 0-1",
                "risk_score": "float 0-1",
                "recommendation": "string",
            },
        )

        confidence = result.get("confidence", 0.6)
        risk_score = result.get("risk_score", 0.5)

        return {
            "analysis": result,
            "confidence": confidence,
            "risk_score": risk_score,
            "severity": context.get("severity"),
            "patch_strategy": result.get("patch_strategy", "update_dependency"),
        }

    async def _reason_fix_validation(self, context: Dict, prior: Dict) -> Dict[str, Any]:
        """Validate that a proposed fix doesn't introduce security issues."""
        # ─── DEMO MODE ───
        if settings.DEMO_MODE:
            return {
                "analysis": {"recommendation": "Fix validated — no new vulnerabilities introduced"},
                "confidence": 0.88,
                "risk_score": 0.12,
                "validation_passed": True,
            }

        result = await self.reasoning_engine.reason(
            system_prompt=SECURITY_SYSTEM_PROMPT,
            context=f"""Validate the security implications of this pipeline fix.
Error context: {context.get('error_logs', '')[:500]}
Ensure no new vulnerabilities are introduced.""",
            reasoning_framework="chain_of_thought",
        )

        return {
            "analysis": result,
            "confidence": result.get("confidence", 0.7),
            "risk_score": result.get("risk_score", 0.3),
            "validation_passed": result.get("confidence", 0.7) > 0.5,
        }

    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the security patch."""
        strategy = reasoning.get("patch_strategy", "update_dependency")
        analysis = reasoning.get("analysis", {})

        return {
            "chosen_action": strategy,
            "confidence": reasoning.get("confidence", 0.6),
            "risk_score": reasoning.get("risk_score", 0.5),
            "reasoning": analysis.get("recommendation", "Apply security patch"),
            "patch_details": analysis,
        }

    async def act(self, plan: Dict[str, Any], task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Execute security patch."""
        tools_used = []
        outputs = {}

        package = task.input_data.get("package", "unknown")
        fixed_version = task.input_data.get("fixed_version", "latest")

        # Generate patch via Claude
        fix_result = await self.reasoning_engine.reason(
            system_prompt=SECURITY_SYSTEM_PROMPT,
            context=f"""Generate a security patch:
Package: {package}
Target version: {fixed_version}
Strategy: {plan.get('chosen_action')}

Provide files_to_modify with exact changes.""",
            output_schema={
                "fix_description": "string",
                "files_to_modify": [{"path": "string", "changes": "string"}],
                "commit_message": "string",
            },
        )

        outputs["patch"] = fix_result
        outputs["branch_name"] = f"autoforge/security-patch-{task.task_id}"

        try:
            from tools.gitlab_tools import GitLabTools
            gitlab_tools = GitLabTools()

            project_id = task.input_data.get("project_id")
            if project_id:
                branch = outputs["branch_name"]
                ref = task.input_data.get("ref", "main")

                await gitlab_tools.create_branch(project_id, branch, ref)
                tools_used.append("create_branch")

                for f in fix_result.get("files_to_modify", []):
                    await gitlab_tools.edit_file(
                        project_id, f["path"], f["changes"], branch,
                        fix_result.get("commit_message", "fix: security patch"),
                    )
                    tools_used.append("edit_file")

                mr = await gitlab_tools.create_merge_request(
                    project_id, branch, ref,
                    title=f"🔐 Security Patch: {package} → {fixed_version}",
                    description=f"## Security Patch\n\n{fix_result.get('fix_description', '')}\n\n*🤖 AutoForge Security Agent*",
                )
                tools_used.append("create_merge_request")
                outputs["merge_request"] = mr

        except Exception as e:
            outputs["execution_mode"] = "simulated"
            outputs["error"] = str(e)

        workflow.add_timeline_entry(
            "security_patch_applied",
            agent="security",
            detail=f"Patched {package}: {plan.get('chosen_action')}",
            confidence=plan.get("confidence"),
        )

        return {
            "output": outputs,
            "summary": f"Security Agent: Patched {package} ({plan.get('chosen_action')})",
            "tools_used": tools_used,
            "confidence": plan.get("confidence", 0.6),
        }

    async def reflect(self, result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Reflect on security patch."""
        if settings.DEMO_MODE:
            from demo.engine import get_demo_reflection
            reflection = get_demo_reflection("security_vulnerability")
            if reflection:
                return reflection

        return await self.reasoning_engine.reflect(
            system_prompt=SECURITY_SYSTEM_PROMPT,
            action_taken=plan.get("chosen_action", "security patch"),
            outcome=result.get("summary", ""),
            context=f"Tools: {result.get('tools_used', [])}",
        )
