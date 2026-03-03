"""
AutoForge SRE Agent — Pipeline Failure Intelligence Unit.

The flagship agent that:
- Diagnoses CI/CD pipeline failures
- Parses logs and identifies root causes
- Detects dependency issues
- Generates code/config fixes
- Creates merge requests with fixes
- Learns from past failures
- Supports DEMO_MODE for deterministic reasoning
"""

from typing import Any, Dict, List
from uuid import uuid4

from config import settings
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
    2. Reason: Generate failure hypotheses (multi-depth tree)
    3. Plan: Select optimal fix strategy
    4. Act: Apply fix and create PR
    5. Reflect: Validate outcome & persist learning
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

        # ─── LIVE MODE: fetch real job logs if we have none ───
        if not settings.DEMO_MODE and not context["error_logs"] and context["pipeline_id"] and context["project_id"]:
            context["error_logs"] = await self._fetch_pipeline_logs(
                context["project_id"], context["pipeline_id"],
            )
            workflow.add_timeline_entry(
                "logs_fetched",
                agent="sre",
                detail=f"Fetched {len(context['error_logs'])} chars of job logs from GitLab",
            )

        # Classify failure type from logs
        context["failure_signals"] = self._extract_failure_signals(
            context.get("error_logs", "")
        )

        # Consume shared context from upstream agents
        shared = input_data.get("_shared_context", {})
        if shared:
            context["upstream_analysis"] = shared

        workflow.add_timeline_entry(
            "perception_complete",
            agent="sre",
            detail=f"Analyzed pipeline {context.get('pipeline_id')} - found {len(context['failure_signals'])} signals",
        )

        return context

    async def _fetch_pipeline_logs(self, project_id: str, pipeline_id: int) -> str:
        """Fetch real job logs from GitLab for failed jobs."""
        try:
            from tools.gitlab_tools import GitLabTools
            tools = GitLabTools()
            result = await tools.get_pipeline_logs(project_id, pipeline_id)
            data = result if isinstance(result, dict) else {}
            if data.get("success"):
                logs = data.get("data", {}).get("logs", {})
                return "\n---\n".join(f"[{name}]\n{text}" for name, text in logs.items())
        except Exception:
            pass
        return ""

    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Generate and evaluate failure hypotheses with multi-depth reasoning tree."""
        # ─── DEMO MODE: use precomputed reasoning ───
        if settings.DEMO_MODE:
            return self._demo_reason(context, prior_knowledge)

        # ─── LIVE MODE: full Claude reasoning ───
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

        return self._build_reasoning_result(hypotheses, context, prior_knowledge)

    def _demo_reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Precomputed reasoning for demo mode — instant, deterministic."""
        from demo.engine import get_demo_scenario

        event_type = context.get("retry_context", {}).get("original_task", "")
        # Detect scenario from error logs
        error_logs = context.get("error_logs", "")
        if "numpy" in error_logs.lower() or "ModuleNotFoundError" in error_logs:
            scenario_key = "pipeline_failure"
        elif "CVE" in error_logs or "vulnerability" in error_logs.lower():
            scenario_key = "security_vulnerability"
        else:
            scenario_key = "pipeline_failure"  # Default

        scenario = get_demo_scenario(scenario_key) or {}
        hypotheses = scenario.get("hypotheses", [])

        return self._build_reasoning_result(hypotheses, context, prior_knowledge)

    def _build_reasoning_result(
        self,
        hypotheses: List[Dict],
        context: Dict[str, Any],
        prior_knowledge: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build multi-depth reasoning tree with evidence weighting."""
        # Build root node
        root = ReasoningNode(
            node_id="root",
            hypothesis="Pipeline Failure Analysis",
            probability=1.0,
            depth=0,
        )

        for i, h in enumerate(hypotheses):
            # ─── Evidence weighting formula ───
            log_match = self._compute_evidence_match(h, context)
            historical_success = prior_knowledge.get("historical_success_rate", 0.0)
            base_prob = h.get("probability", 0.2)

            weighted_confidence = (
                base_prob * 0.5
                + log_match * 0.3
                + historical_success * 0.2
            )

            # Depth-1 node
            child = ReasoningNode(
                node_id=f"h_{i}",
                hypothesis=h.get("description", f"Hypothesis {i}"),
                probability=round(weighted_confidence, 3),
                risk_level=h.get("risk_if_wrong", 0.5),
                evidence=h.get("evidence", []),
                depth=1,
            )

            # ─── Depth-2 sub-hypotheses: drill into top hypotheses ───
            if weighted_confidence > 0.3 and h.get("suggested_action"):
                # Sub-hypothesis: the fix itself
                fix_node = ReasoningNode(
                    node_id=f"h_{i}_fix",
                    hypothesis=f"Fix: {h.get('suggested_action', '')}",
                    probability=weighted_confidence * 0.9,
                    risk_level=h.get("risk_if_wrong", 0.5) * 0.5,
                    evidence=[f"Based on: {h.get('description', '')}"],
                    depth=2,
                )
                child.children.append(fix_node)

                # Sub-hypothesis: alternative approach
                alt_node = ReasoningNode(
                    node_id=f"h_{i}_alt",
                    hypothesis=f"Alternative: manual investigation of {h.get('description', 'root cause')[:50]}",
                    probability=weighted_confidence * 0.3,
                    risk_level=0.1,
                    evidence=["Fallback if primary fix fails"],
                    depth=2,
                )
                child.children.append(alt_node)

            root.children.append(child)

        # Select best hypothesis
        best_idx = 0
        if hypotheses:
            best_idx = max(
                range(len(root.children)),
                key=lambda i: root.children[i].probability,
            )
            root.children[best_idx].selected = True
            # Also select the fix sub-node
            if root.children[best_idx].children:
                root.children[best_idx].children[0].selected = True

        # Calculate tree depth
        max_depth = max((2 if c.children else 1) for c in root.children) if root.children else 0

        reasoning_tree = ReasoningTree(
            root=root,
            total_branches=sum(1 + len(c.children) for c in root.children),
            max_depth=max_depth,
            selected_path=[f"h_{best_idx}", f"h_{best_idx}_fix"] if root.children else [],
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
                confidence=root.children[i].probability if i < len(root.children) else 0.2,
            ))

        # Aggregate scores
        best_h = hypotheses[best_idx] if hypotheses else {}
        best_prob = root.children[best_idx].probability if root.children else 0.5
        confidence = best_prob
        risk_score = 1.0 - confidence

        return {
            "hypotheses": hypotheses,
            "selected_hypothesis": best_idx if hypotheses else 0,
            "root_cause": best_h.get("description", "Unknown"),
            "confidence": round(confidence, 3),
            "risk_score": round(risk_score, 3),
            "reasoning_tree": reasoning_tree.to_visualization(),
            "exploration_depth": reasoning_tree.max_depth,
            "evidence_weighting": "applied",
        }

    def _compute_evidence_match(self, hypothesis: Dict, context: Dict) -> float:
        """Compute how well hypothesis evidence matches the actual logs."""
        evidence = hypothesis.get("evidence", [])
        error_logs = context.get("error_logs", "").lower()
        failure_signals = context.get("failure_signals", [])

        if not evidence or not error_logs:
            return 0.0

        matches = 0
        for e in evidence:
            e_lower = e.lower()
            # Check if evidence keywords appear in logs or signals
            if any(word in error_logs for word in e_lower.split() if len(word) > 4):
                matches += 1
            elif any(signal in e_lower for signal in failure_signals):
                matches += 1

        return min(matches / max(len(evidence), 1), 1.0)

    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Select optimal fix strategy."""
        # ─── DEMO MODE ───
        if settings.DEMO_MODE:
            from demo.engine import get_demo_plan
            error_logs = ""  # We'll use pipeline_failure default
            plan = get_demo_plan("pipeline_failure")
            if plan:
                return plan

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

        # ─── DEMO MODE: use precomputed fix ───
        if settings.DEMO_MODE:
            from demo.engine import get_demo_fix
            fix_result = get_demo_fix("pipeline_failure")
            if not fix_result:
                fix_result = {"fix_description": "Demo fix", "files_to_modify": [], "commit_message": "fix: demo", "branch_name": "autoforge/demo-fix"}
        else:
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

        # Publish fix details to shared context for downstream agents
        workflow.publish_context("sre", "fix_plan", fix_result)
        workflow.publish_context("sre", "root_cause", plan.get("reasoning", ""))
        workflow.publish_context("sre", "files_modified", outputs["files_modified"])
        workflow.publish_context("sre", "branch_name", outputs["branch_name"])

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
        # ─── DEMO MODE ───
        if settings.DEMO_MODE:
            from demo.engine import get_demo_reflection
            reflection = get_demo_reflection("pipeline_failure")
            if reflection:
                return reflection

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
