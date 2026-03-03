# AutoForge — Devpost Submission Draft

## Project Name
AutoForge — Autonomous AI Engineering Orchestrator for GitLab

## Tagline
Six AI agents that autonomously diagnose, fix, secure, test, review, and optimize your GitLab projects — with built-in sustainability tracking.

## What it does

AutoForge is a multi-agent AI system built on the GitLab Duo Agent Platform that transforms how teams handle routine DevOps work. Instead of a single chatbot, AutoForge deploys **six specialized AI agents** that work together through structured cognitive pipelines:

- **🛠 SRE Agent** — Automatically diagnoses CI/CD pipeline failures, generates root cause hypotheses with confidence scores, and creates fix merge requests
- **🔐 Security Agent** — Scans code for vulnerabilities (CVEs, injection, XSS), assesses severity, and applies security patches
- **🌱 GreenOps Agent** — Measures pipeline energy consumption in kWh, calculates CO₂ emissions, and optimizes CI/CD configs for sustainability
- **🧪 QA Agent** — Generates tests covering fixes and detects regressions
- **📝 Review Agent** — Provides structured code reviews with performance and architecture analysis
- **🧾 Docs Agent** — Maintains changelogs and documentation

Each agent follows a **5-phase cognitive pipeline**: Perceive → Reason (Tree-of-Thought) → Plan → Act → Reflect, generating structured hypotheses with evidence-weighted confidence scores.

## How we built it

### GitLab Duo Agent Platform Integration
- **3 Custom Flows** (Flow Registry v1 YAML):
  - SRE Pipeline Fix Flow (4-component: perceive → reason → act → reflect)
  - Security Vulnerability Fix Flow (3-component: scan → assess → patch)
  - GreenOps Sustainability Audit Flow (3-component: audit → analyze → optimize)
- **3 Custom Agents** with specialized system prompts and tool configurations
- **AGENTS.md** for repository-level agent customization

### Architecture
- **Backend**: FastAPI (Python) with 6 AI agents, DAG-based workflow orchestration, policy engine, approval queue
- **Reasoning Engine**: Anthropic Claude via GitLab Duo — Tree-of-Thought hypothesis generation, structured JSON output
- **Dashboard**: Next.js 14 monitoring UI with reasoning tree visualization, GreenOps carbon tracking, agent communication graphs
- **Persistence**: PostgreSQL + Redis + ChromaDB vector store for agent learning
- **Safety**: Branch protection, diff size limits, high-risk action approval gates, RBAC

### Key Technical Decisions
- **Tree-of-Thought Reasoning**: Agents generate 5 hypotheses per problem, each with probability, evidence, and risk scores — not just a single answer
- **DAG Wave Execution**: Tasks execute in dependency waves (SRE first → downstream agents consume context) — not a flat queue
- **GreenOps Energy Model**: Real energy calculations using TDP × duration × grid carbon intensity
- **Dual-Mode Architecture**: DEMO_MODE provides deterministic precomputed reasoning for demonstrations; production mode uses live Claude API calls

### Testing
- **464 automated tests** covering agents, API, orchestration, auth, memory, telemetry
- Integration tests validating full webhook → orchestration → fix → MR pipeline

## Challenges we ran into

1. **Prompt engineering for structured reasoning**: Getting Claude to consistently produce 5 ranked hypotheses with valid probability distributions required iterative prompt refinement
2. **DAG dependency resolution**: Ensuring downstream agents wait for upstream context without deadlocking, with proper retry and escalation
3. **GreenOps accuracy**: Energy estimates need to balance precision with available data — we use conservative TDP-based estimates with clear methodology
4. **Safety guardrails**: Preventing autonomous agents from pushing to protected branches or making oversized changes required a policy engine

## What we learned

- Multi-agent systems need **explicit context sharing** — agents can't just run independently
- **Confidence thresholds** matter: agents should escalate to humans when uncertain, not guess
- **Sustainability metrics** resonate with teams when expressed as concrete numbers (kWh, kg CO₂) rather than abstract scores
- The GitLab Duo Agent Platform tools are powerful enough to build complete autonomous workflows

## What's next for AutoForge

- **Learning loop**: Agents improve from past fix outcomes stored in vector memory
- **Cross-project intelligence**: Pattern recognition across an organization's projects
- **Pipeline-as-Code optimization**: GreenOps agent that continuously monitors and auto-tunes CI/CD configs
- **Approval workflows**: Human-in-the-loop gates for high-risk automated changes

## Built with

- GitLab Duo Agent Platform
- Anthropic Claude (via GitLab Duo)
- Python / FastAPI
- Next.js 14
- PostgreSQL + Redis + ChromaDB
- Docker

## Prize categories

- Grand Prize
- Most Technically Impressive
- Most Impactful
- Green Agent Prize
- Sustainable Design Bonus
- Most Impactful on GitLab & Anthropic
