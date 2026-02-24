"""
AutoForge Documentation Agent — Technical Writer Intelligence.

Updates changelogs, generates API docs, and maintains README files.
Supports DEMO_MODE.
"""

from typing import Any, Dict
from config import settings
from agents.base_agent import BaseAgent
from agents.reasoning_engine import ReasoningEngine
from models.workflows import AgentTask, Workflow

DOCS_SYSTEM_PROMPT = """You are an expert Technical Writer AI in the AutoForge autonomous engineering organization.

Your responsibilities:
- Update changelogs after fixes and features
- Generate and update API documentation
- Maintain README accuracy
- Create clear, concise technical summaries

Guidelines:
- Use conventional changelog format (Added, Fixed, Changed, Removed)
- Write for developer audiences
- Include relevant technical details
- Keep documentation concise but complete"""


class DocsAgent(BaseAgent):
    """Documentation Agent — automated technical writing."""

    def __init__(self):
        super().__init__(
            agent_type="docs",
            capabilities=[
                "changelog_update",
                "api_doc_generation",
                "readme_update",
                "technical_summary",
            ],
        )
        self.reasoning_engine = ReasoningEngine()

    async def perceive(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        return {
            "action": task.action,
            "project_id": task.input_data.get("project_id"),
            "commit_message": task.input_data.get("commit_message", ""),
            "changed_files": task.input_data.get("changed_files", []),
            "mr_title": task.input_data.get("mr_title", ""),
            "ref": task.input_data.get("ref", "main"),
            "error_logs": task.input_data.get("error_logs", ""),
        }

    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        if settings.DEMO_MODE:
            return {
                "analysis": {
                    "docs_needed": ["changelog", "readme"],
                    "changelog_entry": "### Fixed\n- Re-added numpy dependency removed during cleanup refactor\n- Pipeline now passes all 24 tests",
                    "readme_updates": "Updated dependency list in README",
                    "confidence": 0.90,
                },
                "confidence": 0.90,
                "risk_score": 0.05,
            }

        result = await self.reasoning_engine.reason(
            system_prompt=DOCS_SYSTEM_PROMPT,
            context=f"""Determine documentation updates needed:

Action: {context.get('action')}
Changed files: {context.get('changed_files', [])}
Commit: {context.get('commit_message', '')}
MR: {context.get('mr_title', '')}
Context: {context.get('error_logs', '')[:300]}

What documentation should be updated?""",
            output_schema={
                "docs_needed": ["string"],
                "changelog_entry": "string",
                "readme_updates": "string",
                "confidence": "float 0-1",
            },
        )

        return {
            "analysis": result,
            "confidence": result.get("confidence", 0.8),
            "risk_score": 0.1,
        }

    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        analysis = reasoning.get("analysis", {})
        return {
            "chosen_action": "update_documentation",
            "docs_needed": analysis.get("docs_needed", ["changelog"]),
            "changelog_entry": analysis.get("changelog_entry", ""),
            "readme_updates": analysis.get("readme_updates", ""),
            "confidence": reasoning.get("confidence", 0.8),
            "risk_score": 0.1,
            "reasoning": "Update documentation based on changes",
        }

    async def act(self, plan: Dict[str, Any], task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        tools_used = []
        outputs = {}

        if settings.DEMO_MODE:
            doc_result = {
                "files_to_update": [
                    {"path": "CHANGELOG.md", "content": plan.get("changelog_entry", "")},
                ],
                "summary": "Updated CHANGELOG.md with fix entry",
            }
        else:
            # Generate documentation content
            doc_result = await self.reasoning_engine.reason(
            system_prompt=DOCS_SYSTEM_PROMPT,
            context=f"""Generate documentation updates:

Changelog entry: {plan.get('changelog_entry', '')}
README updates: {plan.get('readme_updates', '')}

Generate complete file content for updates.""",
            output_schema={
                "files_to_update": [{"path": "string", "content": "string"}],
                "summary": "string",
            },
        )

        outputs["doc_updates"] = doc_result.get("files_to_update", [])

        try:
            from tools.gitlab_tools import GitLabTools
            gitlab_tools = GitLabTools()
            project_id = task.input_data.get("project_id")
            if project_id:
                for doc in outputs.get("doc_updates", []):
                    await gitlab_tools.edit_file(
                        project_id, doc["path"], doc["content"],
                        f"autoforge/docs-{task.task_id}",
                        "docs: update documentation by AutoForge Docs Agent",
                    )
                    tools_used.append("update_docs")
        except Exception:
            outputs["execution_mode"] = "simulated"

        workflow.add_timeline_entry(
            "docs_updated",
            agent="docs",
            detail=f"Updated {len(outputs.get('doc_updates', []))} documentation files",
            confidence=plan.get("confidence"),
        )

        return {
            "output": outputs,
            "summary": f"Docs Agent: Updated {len(outputs.get('doc_updates', []))} files",
            "tools_used": tools_used,
            "confidence": plan.get("confidence", 0.8),
        }

    async def reflect(self, result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "outcome": result.get("summary", ""),
            "confidence": plan.get("confidence", 0.8),
            "extracted_skill": "documentation_update_pattern",
        }
