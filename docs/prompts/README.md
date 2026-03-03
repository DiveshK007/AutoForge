# AutoForge — Prompt Engineering

## Overview

AutoForge externalises all LLM prompts into YAML templates (`prompts/agents.yaml`) rather than embedding them in Python source code. This separation enables:

- **Rapid iteration** — edit prompts without touching agent logic
- **Version control** — prompt diffs are clean and reviewable
- **A/B testing** — swap prompt files at runtime
- **Transparency** — judges/reviewers can audit prompts in one file

## Architecture

```
prompts/
├── agents.yaml    # All agent prompts (192 lines, 6 agents × 3 phases)
└── loader.py      # YAML → rendered string with variable substitution
```

### Loader API

```python
from prompts.loader import load_prompt

# Load a specific prompt, rendering template variables
prompt = load_prompt("sre", "diagnosis", {
    "error_logs": log_text,
    "failure_signals": signals,
    "commit_message": commit,
    "prior_fixes": memory_recall,
})
```

The loader:
1. Reads `agents.yaml` (cached after first load)
2. Looks up `agent_name → phase_name`
3. Renders `{variable}` placeholders with the provided context dict
4. Falls back to inline Python constants if YAML or PyYAML is unavailable

## Prompt Structure Per Agent

Each agent has up to 3 prompt phases:

| Phase | Purpose | Used When |
|-------|---------|-----------|
| `system` | Sets the agent's identity, role, and behavioural constraints | Every LLM call (system message) |
| `diagnosis` / `analysis` | Structured analysis of the incoming event | Perception + Reasoning phases |
| `fix_generation` / `action` | Generates the concrete remediation plan | Planning + Execution phases |

## Agents Covered

| Agent | Prompts | Key Focus |
|-------|---------|-----------|
| **SRE** | `system`, `diagnosis`, `fix_generation` | Pipeline failure root-cause analysis, minimal safe fixes |
| **Security** | `system`, `analysis` | CVE detection, CVSS scoring, patch generation |
| **QA** | `system`, `analysis` | Test generation, regression detection, coverage gaps |
| **Review** | `system`, `analysis` | Architecture violations, performance anti-patterns |
| **Docs** | `system`, `analysis` | Changelog generation, API doc updates |
| **GreenOps** | `system`, `analysis` | Carbon scoring, pipeline waste identification |

## Design Principles

1. **Structured output** — Every prompt asks for numbered steps, confidence scores, and evidence
2. **Safety-first** — Prompts emphasise minimal changes, risk assessment, and human escalation
3. **Memory-aware** — Prompts include `{prior_fixes}` slots for injecting recall from MemoryStore
4. **Honest confidence** — Agents are explicitly told to "score your confidence honestly"
5. **Multi-hypothesis** — Prompts require considering alternative causes before deciding

## Runtime Flow

```
Event arrives
  → Agent.perceive() extracts context
  → memory.recall() fetches prior knowledge
  → load_prompt(agent, "diagnosis", context) → rendered prompt
  → Claude Sonnet 4 API call (or DEMO_MODE precomputed response)
  → Agent.reason() parses structured output
  → Agent.plan() selects best hypothesis
  → Agent.act() executes tools
  → Agent.reflect() generates learning summary
```

In `DEMO_MODE=true`, the prompt loading still occurs but the LLM call is short-circuited with precomputed reasoning trees from `backend/demo/engine.py`.
