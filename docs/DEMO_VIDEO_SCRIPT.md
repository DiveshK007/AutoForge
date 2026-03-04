# Demo Video Script — AutoForge (3 minutes)

> **Recording tip**: Use screen recording (QuickTime/OBS), speak clearly, keep a steady pace.
> All URLs below are live and publicly accessible.

---

## 0:00–0:15 — Hook (15 sec)

**Say**: "What if AI agents could autonomously diagnose pipeline failures, find security vulnerabilities, and measure your carbon footprint — all running natively inside GitLab?"

**Show**: Open the GitLab project page:
- https://gitlab.com/gitlab-ai-hackathon/participants/35031168
- Scroll to show the repo structure: `agents/`, `flows/`, `AGENTS.md`

---

## 0:15–0:40 — The Problem (25 sec)

**Say**: "DevOps teams spend over 40% of their time on reactive work — debugging CI failures, triaging security issues, and nobody tracks the environmental cost of running thousands of pipelines. AutoForge solves all three with specialized AI agents on the GitLab Duo Agent Platform."

**Show**: Quick scroll through the 6 YAML files:
- `agents/sre_agent.yml`, `agents/security_agent.yml`, `agents/greenops_agent.yml`
- `flows/sre_flow.yml`, `flows/security_flow.yml`, `flows/greenops_flow.yml`

---

## 0:40–1:15 — Demo 1: SRE Agent (35 sec)

**Say**: "First, the SRE Agent. We @mention its service account on a merge request with a pipeline failure."

**Show** (navigate in browser):
1. Open [MR !6](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/merge_requests/6)
2. Scroll to the comment showing `@ai-autoforge-sre-pipeline-fix-gitlab-ai-hackathon` mention
3. Show the "✅ has started" response from the service account
4. Open [SRE Flow Session #3046329](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046329)
5. Show the session log — agent perceiving, reasoning, planning, acting

**Say**: "The agent follows a 5-phase cognitive pipeline — Perceive, Reason with Tree-of-Thought, Plan, Act, Reflect. It generates multiple hypotheses with confidence scores, not just a single answer."

---

## 1:15–1:45 — Demo 2: Security Agent (30 sec)

**Say**: "Next, the Security Agent. We trigger it by @mentioning on an issue."

**Show**:
1. Open [Issue #16](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/16)
2. Show the @mention and "✅ has started" response
3. Open [Security Flow Session #3046331](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046331)
4. Show session log — scanning, assessing CVSS scores, planning patches

**Say**: "Earlier in Duo Chat, this agent found 12 vulnerabilities in a single scan — each one documented as a tracked issue."

**Show**: Quickly scroll the [Issues list](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues) showing Issues #4–#15

---

## 1:45–2:20 — Demo 3: GreenOps Agent (35 sec)

**Say**: "Finally, our GreenOps Agent — this is what makes AutoForge unique. It measures the actual energy consumption and carbon footprint of your CI/CD pipelines."

**Show**:
1. Open [Issue #17](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/17)
2. Show the @mention and "✅ has started" response
3. Open [GreenOps Flow Session #3046334](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046334)
4. Show session log — auditing pipeline, calculating energy (TDP × duration × cores), CO₂ emissions

**Say**: "It uses real physics — thermal design power times duration times core count times grid carbon intensity. Not an abstract score, but real kilowatt-hours and kilograms of CO₂."

---

## 2:20–2:45 — Architecture & All Pipelines Succeeded (25 sec)

**Say**: "All three flows run as duo_workflow pipelines on GitLab's infrastructure. Let me show you — all three succeeded."

**Show**: Navigate to [Pipelines page](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/pipelines) and show:
- Pipeline #2363023638 (SRE) → ✅ passed
- Pipeline #2363023377 (Security) → ✅ passed
- Pipeline #2363023217 (GreenOps) → ✅ passed

**Say**: "The entire system is built with zero external infrastructure. No API keys, no servers. Everything runs natively on GitLab Duo with Anthropic Claude built in."

---

## 2:45–3:00 — Closing (15 sec)

**Say**: "AutoForge — three specialized AI agents, three orchestration flows, six AI Catalog items. Autonomous DevOps that's fast, secure, and sustainable. Built entirely on the GitLab Duo Agent Platform."

**Show**: Return to the project page and show the README.

---

## Key URLs for Recording

| What | URL |
|------|-----|
| Project | https://gitlab.com/gitlab-ai-hackathon/participants/35031168 |
| MR !6 (SRE) | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/merge_requests/6 |
| Issue #16 (Security) | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/16 |
| Issue #17 (GreenOps) | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/17 |
| SRE Session | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046329 |
| Security Session | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046331 |
| GreenOps Session | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046334 |
| Pipelines | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/pipelines |
| Issues List | https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues |
