# AutoForge — Agent Prompt Library

This directory contains the system prompts and reasoning templates used by each agent.

## Prompt Design Principles

1. **Role clarity** — Each prompt starts with a clear agent identity
2. **Structured output** — JSON schemas enforce consistent LLM responses
3. **Safety rails** — Prompts include explicit constraints (no destructive actions)
4. **Evidence-based** — Prompts require evidence and confidence scores
5. **Reflective** — All prompts include self-critique steps

## Agent Prompts

| Agent | Prompt File | Description |
|-------|-------------|-------------|
| SRE | `backend/agents/sre/prompts.py` | Pipeline diagnosis, fix generation |
| Security | Inline in `agent.py` | CVE analysis, patch strategy |
| QA | Inline in `agent.py` | Test generation, coverage analysis |
| Review | Inline in `agent.py` | Code quality, architecture review |
| Docs | Inline in `agent.py` | Changelog, README updates |
| GreenOps | Inline in `agent.py` | Energy estimation, carbon optimization |

## Reasoning Frameworks

The Reasoning Engine supports 4 frameworks:

1. **Chain-of-Thought** — Linear step-by-step analysis
2. **Tree-of-Thought** — Multi-path hypothesis exploration
3. **ReAct** — Reason + Act iterative loops
4. **Reflection** — Self-critique and refinement
