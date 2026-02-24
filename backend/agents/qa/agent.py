"""
AutoForge QA Agent — Quality Intelligence Unit.

Generates unit tests, validates regression risk,
and ensures code quality. Supports DEMO_MODE.
"""

from typing import Any, Dict
from config import settings
from agents.base_agent import BaseAgent
from agents.reasoning_engine import ReasoningEngine
from models.workflows import AgentTask, Workflow

QA_SYSTEM_PROMPT = """You are an expert QA Engineer AI in the AutoForge autonomous engineering organization.

Your responsibilities:
- Generate comprehensive unit tests
- Identify untested logic paths and edge cases
- Assess regression risk from code changes
- Validate fix correctness through test design
- Improve overall test coverage

Guidelines:
- Write tests that are deterministic and fast
- Cover edge cases and error conditions
- Use appropriate testing frameworks
- Ensure tests are maintainable
- Score test coverage and risk accurately"""


class QAAgent(BaseAgent):
    """QA Agent — generates tests and validates code quality."""

    def __init__(self):
        super().__init__(
            agent_type="qa",
            capabilities=[
                "test_generation",
                "regression_detection",
                "coverage_analysis",
                "edge_case_identification",
            ],
        )
        self.reasoning_engine = ReasoningEngine()

    async def perceive(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Parse QA context."""
        context = {
            "action": task.action,
            "project_id": task.input_data.get("project_id"),
            "diff": task.input_data.get("diff", ""),
            "changed_files": task.input_data.get("changed_files", []),
            "error_logs": task.input_data.get("error_logs", ""),
            "ref": task.input_data.get("ref", "main"),
        }
        # Consume upstream SRE context
        shared = task.input_data.get("_shared_context", {})
        if shared:
            sre_ctx = shared.get("sre", {})
            if sre_ctx:
                context["sre_fix_files"] = sre_ctx.get("files_modified", [])
                context["sre_summary"] = sre_ctx.get("summary", "")
        return context

    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code changes for test requirements."""
        if settings.DEMO_MODE:
            return {
                "analysis": {
                    "test_targets": ["data_processor.py", "analytics.py"],
                    "edge_cases": ["Empty input arrays", "Missing numpy at import time", "Very large matrices"],
                    "regression_risks": ["Removing numpy breaks 3 test files"],
                    "test_framework": "pytest",
                    "coverage_gap_score": 0.35,
                },
                "confidence": 0.82,
                "risk_score": 0.25,
            }

        result = await self.reasoning_engine.reason(
            system_prompt=QA_SYSTEM_PROMPT,
            context=f"""Analyze these code changes for testing needs:

Changed files: {context.get('changed_files', [])}
Code diff: {context.get('diff', 'Not available')[:1000]}
Error context: {context.get('error_logs', '')[:500]}

Identify:
1. What functions/modules need tests?
2. What edge cases should be covered?
3. What regression risks exist?
4. What test framework should be used?""",
            reasoning_framework="chain_of_thought",
            output_schema={
                "test_targets": ["string"],
                "edge_cases": ["string"],
                "regression_risks": ["string"],
                "test_framework": "string",
                "coverage_gap_score": "float 0-1",
                "confidence": "float 0-1",
                "risk_score": "float 0-1",
            },
        )

        return {
            "analysis": result,
            "confidence": result.get("confidence", 0.7),
            "risk_score": result.get("risk_score", 0.4),
        }

    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Plan test generation strategy."""
        analysis = reasoning.get("analysis", {})
        return {
            "chosen_action": "generate_tests",
            "test_targets": analysis.get("test_targets", []),
            "edge_cases": analysis.get("edge_cases", []),
            "framework": analysis.get("test_framework", "pytest"),
            "confidence": reasoning.get("confidence", 0.7),
            "risk_score": reasoning.get("risk_score", 0.4),
            "reasoning": "Generate tests for identified targets and edge cases",
        }

    async def act(self, plan: Dict[str, Any], task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Generate tests."""
        tools_used = []

        if settings.DEMO_MODE:
            test_result = {
                "test_files": [
                    {"path": "tests/test_dependency_check.py", "content": "# Auto-generated dependency validation test\nimport pytest\n\ndef test_numpy_importable():\n    import numpy\n    assert numpy.__version__\n"},
                    {"path": "tests/test_data_processor_edge.py", "content": "# Edge case tests for data processor\nimport pytest\nimport numpy as np\n\ndef test_empty_array():\n    assert np.array([]).size == 0\n\ndef test_large_matrix():\n    m = np.zeros((1000,1000))\n    assert m.shape == (1000,1000)\n"},
                ],
                "test_count": 3,
                "coverage_improvement": "+12% estimated coverage improvement",
            }
        else:
            test_result = await self.reasoning_engine.reason(
            system_prompt=QA_SYSTEM_PROMPT,
            context=f"""Generate unit tests for these targets:

Targets: {plan.get('test_targets', [])}
Edge cases: {plan.get('edge_cases', [])}
Framework: {plan.get('framework', 'pytest')}

Generate complete, runnable test code.""",
            output_schema={
                "test_files": [{"path": "string", "content": "string"}],
                "test_count": "int",
                "coverage_improvement": "string",
            },
        )

        outputs = {
            "tests_generated": test_result.get("test_files", []),
            "test_count": test_result.get("test_count", 0),
            "coverage_improvement": test_result.get("coverage_improvement", ""),
        }

        try:
            from tools.gitlab_tools import GitLabTools
            gitlab_tools = GitLabTools()
            project_id = task.input_data.get("project_id")
            if project_id:
                for test_file in outputs.get("tests_generated", []):
                    await gitlab_tools.edit_file(
                        project_id, test_file["path"], test_file["content"],
                        f"autoforge/qa-tests-{task.task_id}", "test: add automated tests by AutoForge QA Agent",
                    )
                    tools_used.append("create_test_file")
        except Exception:
            outputs["execution_mode"] = "simulated"

        workflow.add_timeline_entry(
            "tests_generated",
            agent="qa",
            detail=f"Generated {outputs.get('test_count', 0)} tests",
            confidence=plan.get("confidence"),
        )

        return {
            "output": outputs,
            "summary": f"QA Agent: Generated {outputs.get('test_count', 0)} tests for {len(plan.get('test_targets', []))} targets",
            "tools_used": tools_used,
            "confidence": plan.get("confidence", 0.7),
        }

    async def reflect(self, result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Reflect on test generation."""
        if settings.DEMO_MODE:
            return {
                "success": True,
                "outcome": result.get("summary", "Tests generated"),
                "confidence": 0.82,
                "extracted_skill": "test_generation_for_dependency_issues",
                "lesson_learned": "Always add import validation tests when dependencies change",
            }
        return await self.reasoning_engine.reflect(
            system_prompt=QA_SYSTEM_PROMPT,
            action_taken="generate_tests",
            outcome=result.get("summary", ""),
            context=f"Tests: {result.get('output', {}).get('test_count', 0)}",
        )
