"""
AutoForge SRE Agent — Pipeline Failure Intelligence Unit.

The flagship agent that:
- Diagnoses CI/CD pipeline failures
- Parses logs and identifies root causes
- Detects dependency issues
- Generates code/config fixes
- Creates merge requests with fixes
- Learns from past failures
"""

from typing import Any, Dict, List
from uuid import uuid4

from agents.base_agent import BaseAgent
from agents.reasoning_engine import ReasoningEngine
from agents.sre.prompts import (
    SRE_SYSTEM_PROMPT,
    SRE_DIAGNOSIS_PROMPT,
    SRE_FIX_GENERATION_PROMPT,
)
from models.workflows import AgentTask, Workflow
from models.agents import ReasoningTree, ReasoningNode, Hypothesis


class SREAgent(BaseAgent):
    """
    Site Reliability Engineering Agent.

    Cognition Pipeline:
    1. Perceive: Parse logs, diffs, configs
    2. Reason: Generate failure hypotheses
    3. Plan: Select optimal fix strategy
    4. Act: Apply fix and create PR
    5. Reflect: Validate outcome
    """

    def __init__(self):
        super().__init__(
            agent_type="sre",
            capabilities=[
                "pipeline_diagnosis",
                "log_analysis",
                "dependency_detection",
                "fix_generation",
                "pr_creation",
                "pipeline_rerun",
            ],
        )
        self.reasoning_engine = ReasoningEngine()

    async def perceive(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Parse pipeline failure context."""
        input_data = task.input_data

        context = {
            "error_logs": input_data.get("error_logs", ""),
            "pipeline_id": input_data.get("pipeline_id"),
            "failed_jobs": input_data.get("failed_jobs", []),
            "commit_sha": input_data.get("commit_sha"),
            "commit_message": input_data.get("commit_message"),
            "project_id": input_data.get("project_id"),
            "ref": input_data.get("ref", "main"),
            "retry_context": input_data.get("retry_context"),
        }

        # Classify failure type from logs
        context["failure_signals"] = self._extract_failure_signals(
            context.get("error_logs", "")
        )

        workflow.add_timeline_entry(
            "perception_complete",
            agent="sre",
            detail=f"Analyzed pipeline {context.get('pipeline_id')} - found {len(context['failure_signals'])} signals",
        )

        return context

    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Generate and evaluate failure hypotheses."""
        # Build context prompt
        diagnosis_context = SRE_DIAGNOSIS_PROMPT.format(
            error_logs=context.get("error_logs", "No logs available"),
            failure_signals=context.get("failure_signals", []),
            commit_message=context.get("commit_message", "No commit info"),
            prior_fixes=prior_knowledge.get("similar_fixes", "No prior knowledge"),
        )

        # Generate hypotheses via Claude
        hypotheses = await self.reasoning_engine.generate_hypotheses(
            system_prompt=SRE_SYSTEM_PROMPT,
            context=diagnosis_context,
            max_hypotheses=5,
        )

        # Build reasoning tree
        root = ReasoningNode(
            node_id="root",
            hypothesis="Pipeline Failure",
            probability=1.0,
            depth=0,
        )

        for i, h in enumerate(hypotheses):
            child = ReasoningNode(
                node_id=f"h_{i}",
                hypothesis=h.get("description", f"Hypothesis {i}"),
                probability=h.get("probability", 0.2),
                risk_level=h.get("risk_if_wrong", 0.5),
                evidence=h.get("evidence", []),
                depth=1,
            )
            root.children.append(child)

        # Select highest probability hypothesis
        if hypotheses:
            best_idx = max(range(len(hypotheses)), key=lambda i: hypotheses[i].get("probability", 0))
            if root.children:
                root.children[best_idx].selected = True

        reasoning_tree = ReasoningTree(
            root=root,
            total_branches=len(hypotheses),
            max_depth=1,
            selected_path=[f"h_{best_idx}"] if hypotheses else [],
            exploration_score=len(hypotheses) / 5.0,
        )

        self._reasoning_trees.append(reasoning_tree)

        # Store hypotheses
        for i, h in enumerate(hypotheses):
            self._hypotheses.append(Hypothesis(
                hypothesis_id=f"h_{uuid4().hex[:8]}",
                description=h.get("description", ""),
                probability=h.get("probability", 0.2),
                evidence=h.get("evidence", []),
                risk_if_wrong=h.get("risk_if_wrong", 0.5),
                suggested_action=h.get("suggested_action", ""),
                confidence=h.get("probability", 0.2),
            ))

        # Calculate aggregate scores
        best_h = hypotheses[best_idx] if hypotheses else {}
        confidence = best_h.get("probability", 0.5)
        risk_score = 1.0 - confidence

        return {
            "hypotheses": hypotheses,
            "selected_hypothesis": best_idx if hypotheses else 0,
            "root_cause": best_h.get("description", "Unknown"),
            "confidence": confidence,
            "risk_score": risk_score,
            "reasoning_tree": reasoning_tree.to_visualization(),
            "exploration_depth": len(hypotheses),
        }

    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Select optimal fix strategy."""
        hypotheses = reasoning.get("hypotheses", [])
        selected_idx = reasoning.get("selected_hypothesis", 0)

        if not hypotheses:
            return {
                "chosen_action": "manual_review",
                "confidence": 0.3,
                "risk_score": 0.7,
                "steps": ["Escalate to human review"],
            }

        # Use Claude to evaluate and plan
        plan = await self.reasoning_engine.evaluate_plan(
            system_prompt=SRE_SYSTEM_PROMPT,
            hypotheses=hypotheses,
            context=f"Selected hypothesis index: {selected_idx}\nRoot cause: {reasoning.get('root_cause', '')}",
        )

        return plan

    async def act(self, plan: Dict[str, Any], task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Execute the fix plan."""
        tools_used = []
        outputs = {}

        chosen_action = plan.get("chosen_action", "")

        # Generate fix code/config via Claude
        fix_prompt = SRE_FIX_GENERATION_PROMPT.format(
            root_cause=plan.get("reasoning", "Unknown cause"),
            chosen_action=chosen_action,
            project_id=task.input_data.get("project_id", ""),
            error_logs=task.input_data.get("error_logs", ""),
        )

        fix_result = await self.reasoning_engine.reason(
            system_prompt=SRE_SYSTEM_PROMPT,
            context=fix_prompt,
            output_schema={
                "fix_description": "string",
                "files_to_modify": [{"path": "string", "changes": "string"}],
                "commit_message": "string",
                "branch_name": "string",
                "tests_to_add": ["string"],
            },
        )

        outputs["fix_plan"] = fix_result
        outputs["files_modified"] = fix_result.get("files_to_modify", [])
        outputs["commit_message"] = fix_result.get("commit_message", "fix: automated pipeline fix by AutoForge SRE Agent")
        outputs["branch_name"] = fix_result.get("branch_name", f"autoforge/sre-fix-{task.task_id}")

        # Execute GitLab operations
        try:
            from tools.gitlab_tools import GitLabTools
            gitlab_tools = GitLabTools()

            project_id = task.input_data.get("project_id")
            if project_id:
                # Create branch
                branch = outputs["branch_name"]
                target_ref = task.input_data.get("ref", "main")
                await gitlab_tools.create_branch(project_id, branch, target_ref)
                tools_used.append("create_branch")

                # Apply file changes
                for file_change in outputs.get("files_modified", []):
                    await gitlab_tools.edit_file(
                        project_id,
                        file_change.get("path", ""),
                        file_change.get("changes", ""),
                        branch,
                        outputs["commit_message"],
                    )
                    tools_used.append("edit_file")

                # Create merge request
                mr = await gitlab_tools.create_merge_request(
                    project_id,
                    source_branch=branch,
                    target_branch=target_ref,
                    title=f"🔧 AutoForge SRE Fix: {fix_result.get('fix_description', 'Pipeline fix')}",
                    description=self._build_mr_description(fix_result, plan),
                )
                tools_used.append("create_merge_request")
                outputs["merge_request"] = mr

        except Exception as e:
            outputs["gitlab_error"] = str(e)
            outputs["execution_mode"] = "simulated"

        workflow.add_timeline_entry(
            "fix_applied",
            agent="sre",
            detail=f"Applied fix: {chosen_action}. Tools: {tools_used}",
            confidence=plan.get("confidence", 0.0),
        )

        return {
            "output": outputs,
            "summary": f"SRE Agent: Diagnosed '{plan.get('reasoning', 'pipeline failure')}' → Applied fix: {chosen_action}",
            "tools_used": tools_used,
            "confidence": plan.get("confidence", 0.0),
        }

    async def reflect(self, result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Reflect on the fix outcome."""
        reflection = await self.reasoning_engine.reflect(
            system_prompt=SRE_SYSTEM_PROMPT,
            action_taken=plan.get("chosen_action", "fix applied"),
            outcome=result.get("summary", ""),
            context=f"Tools used: {result.get('tools_used', [])}\nConfidence: {result.get('confidence', 0.0)}",
        )

        return reflection

    # ─── Internal Helpers ───

    def _extract_failure_signals(self, logs: str) -> List[str]:
        """Extract key failure signals from logs."""
        signals = []
        error_patterns = {
            "ModuleNotFoundError": "missing_dependency",
            "ImportError": "import_failure",
            "SyntaxError": "syntax_error",
            "FileNotFoundError": "missing_file",
            "ConnectionError": "connection_failure",
            "TimeoutError": "timeout",
            "PermissionError": "permission_denied",
            "VersionConflict": "version_conflict",
            "FAILED": "test_failure",
            "ERROR": "general_error",
            "exit code 1": "nonzero_exit",
            "npm ERR": "npm_error",
            "pip install": "pip_failure",
        }

        for pattern, signal in error_patterns.items():
            if pattern.lower() in logs.lower():
                signals.append(signal)

        return signals or ["unknown_failure"]

    def _build_mr_description(self, fix_result: Dict, plan: Dict) -> str:
        """Build a detailed merge request description."""
        return f"""## 🔧 AutoForge Automated Fix

### Root Cause Analysis
{plan.get('reasoning', 'Automated diagnosis')}

### Fix Applied
{fix_result.get('fix_description', 'Automated fix')}

### Files Modified
{chr(10).join(f"- `{f.get('path', '')}`" for f in fix_result.get('files_to_modify', []))}

### Confidence Score
**{plan.get('confidence', 0.0):.0%}**

### Risk Assessment
**{plan.get('risk_score', 0.0):.0%}** risk level

---
*🤖 Generated by AutoForge SRE Agent*
*Powered by Claude reasoning engine*
"""
