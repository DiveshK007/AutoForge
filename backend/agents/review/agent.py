"""
AutoForge Review Agent — Code Quality Intelligence.

Evaluates code quality, detects architecture violations,
performance risks, and security smells.
"""

from typing import Any, Dict
from agents.base_agent import BaseAgent
from agents.reasoning_engine import ReasoningEngine
from models.workflows import AgentTask, Workflow

REVIEW_SYSTEM_PROMPT = """You are a senior Code Review Engineer AI in the AutoForge autonomous engineering organization.

Your responsibilities:
- Evaluate code quality and maintainability
- Detect architecture violations and anti-patterns
- Identify performance risks and bottlenecks
- Flag security smells and vulnerabilities
- Suggest improvements with clear rationale

Guidelines:
- Be constructive and specific
- Prioritize issues by severity
- Provide actionable suggestions
- Consider the broader system context
- Score code quality objectively"""


class ReviewAgent(BaseAgent):
    """Review Agent — code quality and architecture analysis."""

    def __init__(self):
        super().__init__(
            agent_type="review",
            capabilities=[
                "code_quality_analysis",
                "architecture_review",
                "performance_detection",
                "security_smell_detection",
                "best_practice_enforcement",
            ],
        )
        self.reasoning_engine = ReasoningEngine()

    async def perceive(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Parse review context."""
        return {
            "action": task.action,
            "mr_id": task.input_data.get("mr_id"),
            "mr_title": task.input_data.get("mr_title", ""),
            "diff": task.input_data.get("diff", ""),
            "changed_files": task.input_data.get("changed_files", []),
            "project_id": task.input_data.get("project_id"),
        }

    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code for quality issues."""
        result = await self.reasoning_engine.reason(
            system_prompt=REVIEW_SYSTEM_PROMPT,
            context=f"""Review this merge request:

MR Title: {context.get('mr_title', 'Unknown')}
Changed Files: {context.get('changed_files', [])}
Diff: {context.get('diff', 'Not available')[:2000]}

Analyze for:
1. Code quality issues
2. Architecture violations
3. Performance risks
4. Security concerns
5. Best practice violations""",
            reasoning_framework="chain_of_thought",
            output_schema={
                "quality_score": "float 0-1",
                "issues": [{"severity": "string", "type": "string", "description": "string", "file": "string", "suggestion": "string"}],
                "summary": "string",
                "confidence": "float 0-1",
                "risk_score": "float 0-1",
            },
        )

        return {
            "review": result,
            "confidence": result.get("confidence", 0.7),
            "risk_score": result.get("risk_score", 0.3),
        }

    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Plan review actions."""
        review = reasoning.get("review", {})
        issues = review.get("issues", [])

        return {
            "chosen_action": "post_review_comments",
            "issues_found": len(issues),
            "quality_score": review.get("quality_score", 0.0),
            "confidence": reasoning.get("confidence", 0.7),
            "risk_score": reasoning.get("risk_score", 0.3),
            "reasoning": review.get("summary", "Code review complete"),
        }

    async def act(self, plan: Dict[str, Any], task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Post review comments."""
        tools_used = []
        outputs = {"review_plan": plan}

        try:
            from tools.gitlab_tools import GitLabTools
            gitlab_tools = GitLabTools()
            project_id = task.input_data.get("project_id")
            mr_id = task.input_data.get("mr_id")

            if project_id and mr_id:
                review_body = f"""## 🔍 AutoForge Code Review

**Quality Score:** {plan.get('quality_score', 0):.0%}
**Issues Found:** {plan.get('issues_found', 0)}

{plan.get('reasoning', '')}

---
*🤖 AutoForge Review Agent*"""

                await gitlab_tools.comment_on_mr(project_id, mr_id, review_body)
                tools_used.append("comment_on_mr")

        except Exception:
            outputs["execution_mode"] = "simulated"

        workflow.add_timeline_entry(
            "review_posted",
            agent="review",
            detail=f"Review: {plan.get('issues_found', 0)} issues, quality {plan.get('quality_score', 0):.0%}",
            confidence=plan.get("confidence"),
        )

        return {
            "output": outputs,
            "summary": f"Review Agent: Found {plan.get('issues_found', 0)} issues, quality score {plan.get('quality_score', 0):.0%}",
            "tools_used": tools_used,
            "confidence": plan.get("confidence", 0.7),
        }

    async def reflect(self, result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        return await self.reasoning_engine.reflect(
            system_prompt=REVIEW_SYSTEM_PROMPT,
            action_taken="code_review",
            outcome=result.get("summary", ""),
            context=f"Quality: {plan.get('quality_score', 0)}",
        )
