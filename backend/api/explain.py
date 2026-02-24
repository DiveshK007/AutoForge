"""
AutoForge Explain API — Natural-language explanation of agent reasoning.

Provides a human-friendly explanation of:
- Why an agent chose a particular fix
- The reasoning chain behind a workflow
- Memory / prior knowledge that influenced a decision
"""

from fastapi import APIRouter, HTTPException, Request

from logging_config import get_logger

log = get_logger("explain")

router = APIRouter()


def _format_reasoning_explanation(reasoning_chain: list, agents_involved: list) -> str:
    """Convert a raw reasoning chain into a readable narrative."""
    if not reasoning_chain:
        return "No reasoning data available for this workflow."

    lines: list[str] = []
    lines.append("## AutoForge Reasoning Explanation\n")

    for i, step in enumerate(reasoning_chain, 1):
        step_type = step.get("type", "unknown")
        agent = step.get("agent", "system")
        decision = step.get("decision", "")
        detail = step.get("detail", "")
        confidence = step.get("confidence", 0)
        risk = step.get("risk", 0)
        wave = step.get("wave", "")

        if step_type == "agent_execution":
            lines.append(
                f"**Step {i} — {agent.upper()} Agent** (Wave {wave})\n"
                f"- Decision: {decision}\n"
                f"- Detail: {detail}\n"
                f"- Confidence: {confidence:.0%} | Risk: {risk:.0%}\n"
            )
        elif step_type == "reflection":
            lines.append(
                f"**Step {i} — System Reflection**\n"
                f"- {detail}\n"
                f"- Collaboration index: {step.get('collaboration_index', 0):.0%}\n"
                f"- Shared context: {', '.join(step.get('shared_context_keys', []))}\n"
            )
        else:
            lines.append(f"**Step {i}** — {detail}\n")

    lines.append(f"\n**Agents involved:** {', '.join(agents_involved)}")
    return "\n".join(lines)


def _format_scenario_explanation(scenario_key: str, tree_data: dict) -> str:
    """Explain a demo reasoning tree in natural language."""
    nodes = tree_data.get("nodes", [])
    edges = tree_data.get("edges", [])

    if not nodes:
        return "No reasoning data available."

    lines: list[str] = [f"## Reasoning Explanation: {scenario_key.replace('_', ' ').title()}\n"]

    # Group nodes by type for narrative flow
    type_order = ["event", "perception", "hypothesis", "reasoning", "plan", "action", "reflection", "result"]
    node_by_type: dict[str, list] = {}
    for n in nodes:
        ntype = n.get("type", "unknown")
        node_by_type.setdefault(ntype, []).append(n)

    for ntype in type_order:
        group = node_by_type.get(ntype, [])
        if not group:
            continue

        if ntype == "event":
            lines.append(f"**1. Event Trigger:** {group[0].get('label', '')}")
        elif ntype == "perception":
            lines.append(f"\n**2. Perception:** {group[0].get('label', '')}")
        elif ntype == "hypothesis":
            lines.append(f"\n**3. Hypotheses Generated:**")
            for j, h in enumerate(group, 1):
                conf = h.get("confidence", 0)
                lines.append(f"   {j}. {h.get('label', '')} (confidence: {conf:.0%})")
        elif ntype == "reasoning":
            lines.append(f"\n**4. Reasoning:** {group[0].get('label', '')}")
        elif ntype == "plan":
            lines.append(f"\n**5. Chosen Plan:** {group[0].get('label', '')}")
        elif ntype == "action":
            lines.append(f"\n**6. Action Taken:** {group[0].get('label', '')}")
        elif ntype == "reflection":
            lines.append(f"\n**7. Reflection:** {group[0].get('label', '')}")
        elif ntype == "result":
            lines.append(f"\n**8. Result:** {group[0].get('label', '')}")

    avg_conf = sum(n.get("confidence", 0) for n in nodes) / max(len(nodes), 1)
    lines.append(f"\n**Overall confidence:** {avg_conf:.0%}")
    lines.append(f"**Reasoning depth:** {len(nodes)} cognitive steps")
    lines.append(f"**Decision edges:** {len(edges)} connections")

    return "\n".join(lines)


@router.get("/workflow/{workflow_id}")
async def explain_workflow(workflow_id: str, request: Request):
    """
    Get a natural-language explanation of why AutoForge did what it did.

    Returns a human-readable narrative of the entire workflow reasoning chain,
    including which agents were involved, what decisions they made, and why.
    """
    brain = request.app.state.brain

    # Check if it's a demo scenario key
    from config import settings
    if settings.DEMO_MODE:
        from demo.engine import DEMO_REASONING_TREES
        from api.dashboard import _build_demo_reasoning_visualization

        # Resolve alias
        from api.dashboard import _SCENARIO_ALIASES
        resolved = _SCENARIO_ALIASES.get(workflow_id, workflow_id)

        if resolved in DEMO_REASONING_TREES:
            tree = _build_demo_reasoning_visualization(resolved)
            explanation = _format_scenario_explanation(resolved, tree)
            return {
                "workflow_id": workflow_id,
                "explanation": explanation,
                "format": "markdown",
                "reasoning_depth": len(tree.get("nodes", [])),
                "confidence": (
                    sum(n.get("confidence", 0) for n in tree.get("nodes", []))
                    / max(len(tree.get("nodes", [])), 1)
                ),
            }

    # Live workflow
    workflow = brain.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    explanation = _format_reasoning_explanation(
        workflow.reasoning_chain,
        workflow.agents_involved,
    )

    return {
        "workflow_id": workflow_id,
        "explanation": explanation,
        "format": "markdown",
        "agents_involved": workflow.agents_involved,
        "task_count": len(workflow.tasks),
        "duration_seconds": workflow.duration_seconds,
        "status": workflow.status.value,
    }


@router.get("/agent/{agent_type}")
async def explain_agent(agent_type: str, request: Request):
    """
    Explain what a specific agent does, its capabilities, and recent performance.
    """
    brain = request.app.state.brain
    agent = brain.get_agent(agent_type)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")

    stats = agent.get_stats()
    recent = agent.get_recent_actions(limit=5)

    agent_descriptions = {
        "sre": "The SRE Agent is AutoForge's Pipeline Doctor. It diagnoses CI/CD failures by analyzing logs, identifying root causes (missing dependencies, syntax errors, configuration drift), generating code fixes, and creating merge requests — all autonomously.",
        "security": "The Security Agent is a DevSecOps Specialist. It scans for CVEs, evaluates vulnerability severity, generates patches for affected dependencies, and ensures fixes don't introduce new attack surfaces.",
        "qa": "The QA Agent provides Quality Intelligence. It automatically generates regression tests for fixes, validates that changes don't break existing functionality, and tracks test coverage improvements.",
        "review": "The Review Agent acts as an Automated Code Reviewer. It checks architecture violations, performance anti-patterns, code quality, and provides structured feedback with severity ratings.",
        "docs": "The Docs Agent is an Automated Technical Writer. It generates changelogs, updates API documentation, maintains READMEs, and ensures documentation stays synchronized with code changes.",
        "greenops": "The GreenOps Agent is a Sustainability Analyst. It measures carbon footprint of CI/CD pipelines, identifies energy waste, suggests optimizations, and tracks environmental impact over time.",
    }

    return {
        "agent_type": agent_type,
        "description": agent_descriptions.get(agent_type, f"Specialized agent: {agent_type}"),
        "capabilities": agent.capabilities,
        "status": agent.status,
        "stats": stats,
        "recent_actions": recent,
        "explanation": (
            f"The {agent_type.upper()} Agent has completed {stats.get('total_completed', 0)} tasks "
            f"with a {stats.get('success_rate', 0):.0%} success rate and "
            f"{stats.get('avg_confidence', 0):.0%} average confidence."
        ),
    }


@router.get("/decision/{workflow_id}/{agent_type}")
async def explain_decision(workflow_id: str, agent_type: str, request: Request):
    """
    Explain a specific agent's decision within a workflow.
    """
    brain = request.app.state.brain
    workflow = brain.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    # Find the agent's task in this workflow
    agent_task = next(
        (t for t in workflow.tasks if t.agent_type == agent_type),
        None,
    )

    if not agent_task:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_type}' was not involved in workflow {workflow_id}",
        )

    # Find reasoning chain entries for this agent
    agent_steps = [
        step for step in workflow.reasoning_chain
        if step.get("agent") == agent_type
    ]

    return {
        "workflow_id": workflow_id,
        "agent_type": agent_type,
        "task_action": agent_task.action,
        "status": agent_task.status.value,
        "confidence": agent_task.confidence,
        "risk_score": agent_task.risk_score,
        "reasoning_steps": agent_steps,
        "explanation": (
            f"The {agent_type.upper()} Agent was assigned '{agent_task.action}' "
            f"and completed with {agent_task.confidence:.0%} confidence. "
            f"{'It self-corrected during execution.' if agent_task.output_data.get('self_corrected') else ''}"
        ),
    }
