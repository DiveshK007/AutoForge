"""
AutoForge Agent Models — Agent state and reasoning structures.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents in the AutoForge workforce."""
    SRE = "sre"
    SECURITY = "security"
    QA = "qa"
    REVIEW = "review"
    DOCS = "docs"
    GREENOPS = "greenops"


class ReasoningNode(BaseModel):
    """A node in the reasoning tree."""
    node_id: str
    hypothesis: str
    probability: float = 0.0
    risk_level: float = 0.0
    evidence: List[str] = []
    children: List["ReasoningNode"] = []
    selected: bool = False
    depth: int = 0


class ReasoningTree(BaseModel):
    """Complete reasoning tree for a diagnosis."""
    root: ReasoningNode
    total_branches: int = 0
    max_depth: int = 0
    selected_path: List[str] = []
    exploration_score: float = 0.0

    def to_visualization(self) -> Dict[str, Any]:
        """Convert to frontend-friendly visualization format."""
        nodes = []
        edges = []

        def traverse(node: ReasoningNode, parent_id: str = None):
            nodes.append({
                "id": node.node_id,
                "data": {
                    "label": node.hypothesis,
                    "probability": node.probability,
                    "risk": node.risk_level,
                    "selected": node.selected,
                },
                "type": "reasoning" if not node.selected else "selected",
            })
            if parent_id:
                edges.append({
                    "id": f"e_{parent_id}_{node.node_id}",
                    "source": parent_id,
                    "target": node.node_id,
                })
            for child in node.children:
                traverse(child, node.node_id)

        traverse(self.root)
        return {"nodes": nodes, "edges": edges}


class AgentAction(BaseModel):
    """Record of an action taken by an agent."""
    action_id: str
    agent_type: str
    action_type: str
    description: str
    input_summary: str = ""
    output_summary: str = ""
    confidence: float = 0.0
    risk_score: float = 0.0
    success: bool = False
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tools_used: List[str] = []


class AgentExperience(BaseModel):
    """An experience stored in agent memory for learning."""
    experience_id: str
    agent_type: str
    failure_type: str
    context_summary: str
    action_taken: str
    outcome: str
    success: bool
    confidence: float
    fix_time_seconds: float
    reusable_skill: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Hypothesis(BaseModel):
    """A hypothesis generated during reasoning."""
    hypothesis_id: str
    description: str
    probability: float
    evidence: List[str]
    risk_if_wrong: float
    suggested_action: str
    confidence: float
