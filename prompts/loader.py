"""
AutoForge — Prompt Loader

Loads externalized YAML prompt templates and renders them with context variables.
Falls back to inline Python constants if YAML is unavailable.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

# Optional YAML dependency — gracefully degrade
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


_PROMPTS_DIR = Path(__file__).parent
_CACHE: Dict[str, Dict] = {}


def _load_yaml(filename: str = "agents.yaml") -> Dict[str, Any]:
    """Load and cache the YAML prompt file."""
    if filename in _CACHE:
        return _CACHE[filename]

    filepath = _PROMPTS_DIR / filename
    if not filepath.exists() or not HAS_YAML:
        _CACHE[filename] = {}
        return _CACHE[filename]

    with open(filepath) as f:
        data = yaml.safe_load(f) or {}

    _CACHE[filename] = data
    return data


def load_prompt(
    agent_type: str,
    prompt_name: str,
    context: Optional[Dict[str, Any]] = None,
    filename: str = "agents.yaml",
) -> Optional[str]:
    """
    Load a prompt template for an agent.

    Args:
        agent_type: e.g. "sre", "security", "qa"
        prompt_name: e.g. "system", "diagnosis", "fix_generation"
        context: Variables to interpolate into the template
        filename: YAML file to load from

    Returns:
        Rendered prompt string, or None if not found
    """
    data = _load_yaml(filename)
    agent_prompts = data.get(agent_type, {})
    template = agent_prompts.get(prompt_name)

    if template is None:
        return None

    if context:
        try:
            return template.format(**context)
        except KeyError:
            # Return raw template if context vars are missing
            return template

    return template


def list_prompts(agent_type: Optional[str] = None) -> Dict[str, list]:
    """List available prompt templates, optionally filtered by agent."""
    data = _load_yaml()
    if agent_type:
        agent_data = data.get(agent_type, {})
        return {agent_type: list(agent_data.keys())}
    return {k: list(v.keys()) for k, v in data.items() if isinstance(v, dict)}
