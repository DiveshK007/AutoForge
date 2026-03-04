# AutoForge — Devpost Submission

## Project URL
https://gitlab.com/gitlab-ai-hackathon/participants/35031168

## Project Name
**AutoForge** — Autonomous AI Engineering Orchestrator for GitLab

## Tagline
Three autonomous AI agents that diagnose pipeline failures, find security vulnerabilities, and measure carbon footprint — all running natively on the GitLab Duo Agent Platform with Anthropic Claude.

---

## Inspiration

DevOps teams spend **40%+ of their time** on reactive work: debugging CI/CD failures, scanning for vulnerabilities, and manually reviewing pipeline efficiency. These are repetitive, pattern-matching tasks — perfect for AI.

But most AI coding tools are single-purpose chatbots. We asked: **What if you had a team of specialized AI agents, each with deep domain expertise, that could autonomously investigate problems and take action — right inside GitLab?**

The GitLab Duo Agent Platform made this possible. Instead of building external integrations, AutoForge's agents run **natively within GitLab** — reading issues, analyzing merge requests, creating fixes, and reporting results using GitLab's own tools.

The **GreenOps** angle was personal: we wanted to prove that sustainability isn't just a buzzword — it can be measured, tracked, and improved at the CI/CD pipeline level.

---

## What it does

AutoForge deploys **3 specialized AI agents** and **3 orchestration flows** on the GitLab Duo Agent Platform:

### 🛠 SRE Agent — Pipeline Failure Diagnosis & Fix
- Analyzes CI/CD pipeline failures using a **5-phase cognitive pipeline**: Perceive → Reason → Plan → Act → Reflect
- Generates multiple root cause hypotheses with confidence scores using **Tree-of-Thought reasoning**
- Creates fix merge requests automatically
- **Live proof**: Triggered on [MR !6](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/merge_requests/6) → Flow session [#3046329](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046329) → Pipeline [#2363023638](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/pipelines/2363023638) ✅ SUCCESS

### 🔐 Security Agent — Vulnerability Scanning & Patching
- Scans code for OWASP Top 10 vulnerabilities, CVEs, injection flaws, XSS
- Assesses severity using CVSS scoring framework
- Generates actionable security patches
- **Live proof**: Triggered on [Issue #16](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/16) → Flow session [#3046331](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046331) → Pipeline [#2363023377](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/pipelines/2363023377) ✅ SUCCESS

### 🌱 GreenOps Agent — Sustainability Audit & Carbon Tracking
- Measures pipeline energy consumption using real physics: **TDP × duration × core count**
- Calculates CO₂ emissions using regional grid carbon intensity factors
- Generates optimization recommendations with projected savings
- **Live proof**: Triggered on [Issue #17](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/17) → Flow session [#3046334](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046334) → Pipeline [#2363023217](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/pipelines/2363023217) ✅ SUCCESS

### Earlier Agent Testing via Duo Chat
Before flow automation, all 3 agents were validated directly in GitLab Duo Chat:
- SRE Agent → Created [MR !6](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/merge_requests/6) with pipeline fix
- Security Agent → Found 12 vulnerabilities → Created [Issues #4–#15](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues)
- GreenOps Agent → Scored pipeline 48/100 efficiency → Created [Issue #3](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/3)

---

## How we built it

### Pure GitLab Duo Agent Platform (Path A)

AutoForge is built **entirely on the GitLab Duo Agent Platform** — no external servers, no API keys, no infrastructure to manage. Anthropic Claude is accessed natively through GitLab Duo.

### 6 AI Catalog Items Published

| # | Item | Type | Catalog ID |
|---|------|------|------------|
| 1 | AutoForge SRE Agent | Agent | 1004211 |
| 2 | AutoForge Security Agent | Agent | 1004212 |
| 3 | AutoForge GreenOps Agent | Agent | 1004213 |
| 4 | AutoForge SRE Pipeline Fix | Flow | 1004214 |
| 5 | AutoForge Security Vulnerability Fix | Flow | 1004215 |
| 6 | AutoForge GreenOps Sustainability Audit | Flow | 1004216 |

### Agent Architecture

Each agent uses a structured YAML definition with:
- **Specialized system prompts** encoding domain expertise
- **Tool configurations** (read_file, create_file, GitLab API tools)
- **Cognitive pipeline**: Perceive → Reason (Tree-of-Thought) → Plan → Act → Reflect

### Flow Architecture

Each flow is a multi-component orchestration pipeline:

```
SRE Flow (4 components):
  perceive_failure → reason_and_plan → apply_fix → reflect

Security Flow (3 components):
  scan_for_vulnerabilities → assess_and_plan → apply_patches

GreenOps Flow (3 components):
  audit_pipeline → calculate_impact → create_optimizations
```

Components use `prompt_id`, `inputs`, `toolset`, and `routers` for structured reasoning and branching.

### Flow Triggering

Flows are triggered by **@mentioning the auto-created service accounts** on issues/MRs:
- `@ai-autoforge-sre-pipeline-fix-gitlab-ai-hackathon` on merge requests
- `@ai-autoforge-security-vulnerability-fix-gitlab-ai-hackathon` on issues
- `@ai-autoforge-greenops-sustainability-audit-gitlab-ai-hackathon` on issues

Service accounts are automatically provisioned by GitLab's `catalog-sync` when flows are published.

### Key Technical Decisions

- **Tree-of-Thought Reasoning**: Agents generate multiple hypotheses per problem, each with probability, evidence, and risk scores — not just a single answer
- **5-Phase Cognitive Pipeline**: Goes beyond simple prompt→response by adding structured perception, reasoning, planning, action, and reflection phases
- **GreenOps Energy Model**: Real physics-based calculations (TDP × duration × cores × PUE × grid carbon intensity), not arbitrary scores
- **Native Platform Integration**: Zero external dependencies — everything runs within GitLab Duo, leveraging Anthropic Claude through the platform

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                GitLab Project                    │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ SRE Agent│  │ Security │  │ GreenOps │      │
│  │   .yml   │  │Agent .yml│  │Agent .yml│      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │              │              │            │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐      │
│  │ SRE Flow │  │ Security │  │ GreenOps │      │
│  │   .yml   │  │Flow .yml │  │Flow .yml │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │              │              │            │
│       ▼              ▼              ▼            │
│  ┌─────────────────────────────────────────┐    │
│  │      GitLab Duo Agent Platform          │    │
│  │  ┌──────────────────────────────────┐   │    │
│  │  │  Anthropic Claude (built-in)     │   │    │
│  │  └──────────────────────────────────┘   │    │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │read_file │ │create_   │ │GitLab  │  │    │
│  │  │          │ │file      │ │API     │  │    │
│  │  └──────────┘ └──────────┘ └────────┘  │    │
│  └─────────────────────────────────────────┘    │
│       │              │              │            │
│       ▼              ▼              ▼            │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐       │
│  │ MRs     │  │ Issues   │  │ Issues   │       │
│  │ (fixes) │  │ (vulns)  │  │ (audits) │       │
│  └─────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────┘
```

---

## Challenges we ran into

1. **Hackathon sandbox CI restrictions**: The hackathon environment overrides `.gitlab-ci.yml` — only template jobs (`placeholder-test`, `validate-items`) run. We pivoted to triggering flows via @mentions instead of custom CI jobs.

2. **Permission constraints**: As Developer-role participants, we couldn't call `aiCatalogItemConsumerCreate` or `aiFlowTriggerCreate` mutations (require Maintainer+). Discovered that **service accounts are auto-created** by `catalog-sync` — no manual enablement needed.

3. **GraphQL API discovery**: GitLab's Duo/AI GraphQL schema is new and sparsely documented. We iteratively discovered required fields by sending mutations and reading error messages — a form of "error-driven API exploration."

4. **Prompt engineering for structured reasoning**: Getting Claude to consistently produce ranked hypotheses with valid probability distributions, evidence chains, and risk scores required careful system prompt design with explicit output format specifications.

5. **GreenOps accuracy**: Energy estimates must balance precision with available data — we use conservative TDP-based estimates with documented methodology and clear uncertainty bounds.

---

## Accomplishments that we're proud of

- **All 6 AI Catalog items published and functional** — 3 agents + 3 flows, all validated by GitLab's `catalog-sync`
- **All 3 agents tested live in Duo Chat** — producing real MRs, issues, and audit reports
- **All 3 flows triggered and completed successfully** — 3 `duo_workflow` pipelines, 3 agent sessions, zero failures
- **Zero external infrastructure** — everything runs natively on GitLab Duo with Anthropic Claude built-in
- **GreenOps sustainability tracking** — real energy calculations (TDP × duration × cores), not just scores
- **Tree-of-Thought reasoning** — agents generate multiple hypotheses with confidence scoring, not single-shot answers
- **Security Agent found 12 vulnerabilities** in a single scan, each documented as a tracked issue

---

## What we learned

- The GitLab Duo Agent Platform is **production-ready** for multi-agent orchestration — flows, service accounts, and tools work end-to-end
- **Agents run within GitLab have access to Anthropic models by default** — no separate API keys needed
- Multi-agent systems need **explicit context sharing** — agents can't just run independently; flows solve this with component chaining
- **Confidence thresholds matter**: agents should escalate to humans when uncertain, not guess
- **Sustainability metrics resonate** when expressed as concrete numbers (kWh, kg CO₂, estimated cost) rather than abstract scores
- **Service accounts are automatically created** when flows are published to the AI Catalog — a powerful but undocumented feature
- Flow triggering via @mentions is the **simplest and most reliable** activation mechanism

---

## What's next for AutoForge

- **Learning loop**: Agents improve from past fix outcomes stored in vector memory (ChromaDB integration)
- **Cross-project intelligence**: Pattern recognition across an organization's projects
- **Pipeline-as-Code optimization**: GreenOps agent that continuously monitors and auto-tunes CI/CD configs
- **Approval workflows**: Human-in-the-loop gates for high-risk automated changes
- **Additional agents**: QA (test generation), Review (code review), Docs (changelog maintenance) — system prompts already designed
- **Carbon dashboard**: Aggregate sustainability metrics across all projects in a group

---

## Built With

- GitLab Duo Agent Platform
- GitLab AI Catalog (Flow Registry v1)
- Anthropic Claude (via GitLab Duo — built-in, no API key)
- Python
- YAML (Agent & Flow definitions)

---

## Try It

1. Visit the [project on GitLab](https://gitlab.com/gitlab-ai-hackathon/participants/35031168)
2. Check the [AI Catalog items](https://gitlab.com/gitlab-ai-hackathon/participants/35031168) — 6 published agents & flows
3. See live results:
   - [MR !6](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/merge_requests/6) — SRE Agent fix + flow response
   - [Issue #16](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/16) — Security flow triggered
   - [Issue #17](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/issues/17) — GreenOps flow triggered
4. View flow sessions:
   - [SRE Session #3046329](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046329)
   - [Security Session #3046331](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046331)
   - [GreenOps Session #3046334](https://gitlab.com/gitlab-ai-hackathon/participants/35031168/-/automate/agent-sessions/3046334)

---

## Prize Categories

- **🏆 Best Overall Project** ($5,000) — Complete multi-agent system with 6 catalog items, all working end-to-end
- **🤖 Best Use of Anthropic on GitLab** ($4,500) — All agents powered by Anthropic Claude via GitLab Duo, Tree-of-Thought reasoning
- **🌱 Best Green Agent** ($4,000) — GreenOps agent with real energy model (TDP × duration × cores × PUE × grid carbon intensity)
- **🎨 Most Creative Use of GitLab Duo** ($1,000) — @mention-triggered autonomous flows with 5-phase cognitive pipelines
