# AutoForge — Agent Configuration

## Project Context

AutoForge is an autonomous multi-agent DevOps orchestrator for GitLab. It monitors
CI/CD pipelines, diagnoses failures, fixes vulnerabilities, optimizes pipeline
efficiency for sustainability, and creates merge requests — all without human
intervention.

## Agent Behavior Guidelines

When working in this repository, agents should:

1. **Follow the cognitive pipeline**: Perceive → Reason → Plan → Act → Reflect
2. **Generate structured hypotheses** with confidence scores and evidence
3. **Prefer minimal, safe fixes** over complex refactors
4. **Always create fixes on feature branches** — never push to main/master/production
5. **Include tests** for any code changes
6. **Calculate energy/carbon impact** of pipeline changes (GreenOps)
7. **Use conventional commits** (fix:, feat:, docs:, test:, perf:, ci:)

## Repository Structure

- `backend/` — FastAPI Python backend with 6 AI agents
- `dashboard/` — Next.js 14 monitoring dashboard
- `prompts/` — YAML prompt templates for all agents
- `gitlab_duo/` — GitLab Duo Agent Platform flow configurations
- `docs/` — Architecture documentation

## Agent-Specific Instructions

### SRE Agent
- Parse pipeline logs for error patterns (ModuleNotFoundError, SyntaxError, etc.)
- Generate multiple hypotheses ranked by probability
- Create minimal dependency or config fixes
- Always pin dependency versions

### Security Agent
- Check CVE databases for known vulnerabilities
- Analyze code for injection, XSS, CSRF risks
- Recommend the most conservative patch
- Never downgrade security controls

### GreenOps Agent
- Measure pipeline energy consumption in kWh
- Calculate CO₂ emissions using grid carbon intensity
- Identify parallelization and caching opportunities
- Quantify savings in both time and carbon

### QA Agent
- Generate unit tests covering the fix
- Add regression tests preventing recurrence
- Cover edge cases and error paths

### Review Agent
- Check for correctness, style, performance, security
- Flag N+1 queries, missing validation, unused imports
- Provide actionable, constructive feedback

### Docs Agent
- Generate conventional changelog entries
- Update API documentation for new endpoints
- Keep README sections current
