# 🔥 AutoForge — Autonomous AI Engineering Orchestrator for GitLab

> An autonomous multi-agent system that monitors, diagnoses, fixes, secures, optimizes, and documents your software lifecycle — without human intervention.

**This is not one agent. This is an AI DevOps Organization inside GitLab.**

---

## 🧠 What is AutoForge?

AutoForge is an event-driven, multi-agent DevOps automation platform that reasons over software lifecycle signals and autonomously executes remediation, validation, documentation, and optimization workflows.

### The AI Engineering Workforce

| Agent | Role | Capability |
|-------|------|------------|
| 🛠 SRE Agent | Pipeline Doctor | Diagnoses CI/CD failures, generates fixes, creates MRs |
| 🔐 Security Agent | DevSecOps Specialist | Detects CVEs, generates patches, scores risk |
| 🧪 QA Agent | Quality Intelligence | Generates tests, validates regressions |
| 📝 Review Agent | Code Reviewer | Architecture violations, performance risks |
| 🧾 Docs Agent | Technical Writer | Changelogs, API docs, README updates |
| 🌱 GreenOps Agent | Sustainability Analyst | Carbon scoring, pipeline optimization |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                GITLAB PLATFORM              │
│  Pipelines • MRs • Issues • Security Alerts │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│          EVENT INGESTION LAYER              │
│   Webhooks • GitLab APIs • Normalization    │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│          COMMAND BRAIN / ORCHESTRATOR       │
│ Task Router • Planner • State Manager       │
└─────────────────────────────────────────────┘
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│  SRE    │   │Security │   │   QA    │
│ Agent   │   │ Agent   │   │ Agent   │
└─────────┘   └─────────┘   └─────────┘
     ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│ Docs    │   │GreenOps │   │ Review  │
│ Agent   │   │ Agent   │   │ Agent   │
└─────────┘   └─────────┘   └─────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│        EXECUTION & TOOLING LAYER            │
│ Code Edits • PRs • Tests • Config Updates   │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         MEMORY + LEARNING LAYER             │
│ Vector DB • Skill Graph • Policy Store      │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│        TELEMETRY + DASHBOARD LAYER          │
│ Metrics • Reasoning Trees • Learning Curves │
└─────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- GitLab account with API token
- Anthropic API key

### 1. Clone & Configure

```bash
git clone https://github.com/DiveshK007/AutoForge.git
cd AutoForge
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker Compose

```bash
docker-compose up -d
```

### 3. Start Backend (Development)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Start Dashboard (Development)

```bash
cd dashboard
npm install
npm run dev
```

### 5. Configure GitLab Webhook

Point your GitLab project webhook to:
```
https://your-domain/api/v1/webhooks/gitlab
```

Events to enable:
- Pipeline events
- Merge request events
- Push events

---

## 📊 Telemetry Metrics

### Meta-Intelligence Score (MIS) — Weighted 5-Factor Formula

```
MIS = Accuracy × 0.30 + Learning × 0.25 + Reflection × 0.20 + Collaboration × 0.15 + Sustainability × 0.10
```

| Metric | Weight | Formula | What It Measures |
|--------|--------|---------|-----------------|
| Accuracy | 30% | Completed / Total Workflows | Execution reliability |
| Learning | 25% | Confidence Improvement Over Time | Autonomy growth |
| Reflection | 20% | Self-Corrections / Failed Attempts | Self-correction ability |
| Collaboration | 15% | Multi-Agent Workflows / Total | Orchestration depth |
| Sustainability | 10% | Energy Efficiency Score | Carbon awareness |

### Additional Metrics

| Metric | What It Measures |
|--------|-----------------|
| Fix Accuracy | Correct Diagnoses / Total Diagnoses |
| Reasoning Depth | Explored Branches / Max Branches (depth-2 trees) |
| Carbon Efficiency | (Baseline - Optimized) / Baseline × 100 |

---

## 🔀 DAG Execution & Shared Context

AutoForge uses **dependency-aware DAG execution** — not a flat queue.

```
Event: pipeline_failure

Wave 0 (no deps):   [ SRE (diagnose) ]  [ GreenOps (audit) ]
                          │
                          ▼  (shared context flows downstream)
Wave 1 (dep: SRE):  [ Security (validate) ]  [ QA (test) ]  [ Docs (changelog) ]
```

Agents share findings through a **Shared Context Bus**:
- SRE publishes `root_cause`, `fix_branch`, `confidence`
- Downstream agents consume upstream context for informed decisions
- Cross-agent knowledge persists in memory for future workflows

---

## 🛡️ Safety Guardrails

| Guardrail | Description |
|-----------|-------------|
| Branch Protection | Agents cannot push to `main`, `master`, `production`, `release`, `staging` |
| Diff Size Limits | Maximum 500 lines per merge request |
| High-Risk Actions | `force_push`, `delete_branch`, `drop_database`, etc. require human approval |
| Escalation Protocol | Retry → Alternate Agent → Manual Review |
| Policy Learning | Tracks violations and adapts agent behaviour |

---

## 🎮 DEMO_MODE

Set `DEMO_MODE=True` (default) for **deterministic live demos without LLM API calls**.

Precomputed reasoning trees cover 4 scenarios:
- `pipeline_failure` — Missing numpy dependency
- `security_vulnerability` — SQL injection detection
- `merge_request_opened` — Code review and test generation
- `inefficient_pipeline` — GreenOps optimization

All 6 agents produce realistic outputs using precomputed data.

---

## 🧠 Agent Cognition Pipeline

Every agent follows the same cognitive architecture:

```
Perception → Reasoning → Planning → Tool Execution → Reflection → Memory Encoding
```

Each agent generates:
- Structured hypotheses
- Risk-scored alternatives
- Confidence-weighted decisions
- Reflection summaries
- Reusable skill patterns

---

## 🏆 Prize Targeting

- **Most Technically Impressive**: Multi-agent orchestration + autonomous remediation
- **Anthropic Integration**: Claude-powered reasoning agents
- **Sustainability**: GreenOps carbon optimization

---

## 📁 Project Structure

```
AutoForge/
├── backend/                  # FastAPI backend services
│   ├── main.py              # Application entry point
│   ├── config.py            # Settings (DEMO_MODE, API keys, thresholds)
│   ├── brain/               # Command Brain orchestrator
│   │   ├── orchestrator.py  # DAG wave executor + retry/escalation
│   │   ├── task_decomposer.py # Event → DAG tasks with dependency wiring
│   │   ├── router.py        # Event → agent routing rules
│   │   ├── policy_engine.py # Branch protection, diff limits, guardrails
│   │   └── conflict_resolver.py
│   ├── agents/              # Agent workforce (6 agents)
│   │   ├── base_agent.py    # 5-phase cognitive pipeline
│   │   ├── reasoning_engine.py # Claude Sonnet 4 integration
│   │   ├── sre/             # SRE: diagnosis, evidence weighting, depth-2 trees
│   │   ├── security/        # Security: vulnerability scanning, CVE analysis
│   │   ├── qa/              # QA: test generation, regression detection
│   │   ├── review/          # Review: code review, architecture analysis
│   │   ├── docs/            # Docs: changelog, API docs, README updates
│   │   └── greenops/        # GreenOps: carbon scoring, pipeline optimization
│   ├── demo/                # DEMO_MODE precomputed reasoning trees
│   │   └── engine.py        # 4 scenarios × 6 agents
│   ├── memory/              # Memory & learning systems
│   │   └── store.py         # Episodic + Semantic + Cross-Agent + Policy layers
│   ├── models/              # Pydantic data models
│   │   ├── workflows.py     # Shared context bus, DAG dependencies
│   │   ├── events.py        # Normalized events
│   │   └── agents.py        # ReasoningTree, ReasoningNode, Hypothesis
│   ├── telemetry/           # Metrics & observability
│   │   └── collector.py     # 5-factor weighted MIS formula
│   ├── tools/               # Execution tool gateway
│   │   └── gitlab_tools.py  # GitLab API + generate_tests + update_docs
│   ├── tests/               # 75 tests (pytest + pytest-asyncio)
│   │   ├── test_core.py     # Core model/brain tests
│   │   ├── test_api.py      # API endpoint tests
│   │   └── test_audit_improvements.py # DAG, demo, memory, policy tests
│   └── api/                 # FastAPI route handlers
├── dashboard/               # React/Next.js frontend
│   ├── src/
│   │   ├── app/            # Next.js app router (page.tsx)
│   │   ├── components/
│   │   │   ├── workflows/  # DAGView, SharedContextView, Timeline
│   │   │   ├── reasoning/  # ReasoningTree (React Flow)
│   │   │   ├── metrics/    # MISBreakdown, MetaScore
│   │   │   ├── charts/     # MetricsCharts, LearningCurveChart
│   │   │   ├── agents/     # AgentGrid
│   │   │   ├── sustainability/ # SustainabilityPanel
│   │   │   ├── demo/       # DemoTrigger
│   │   │   └── ui/         # GlassCard, MetricCard, StatusBadge
│   │   └── lib/            # API client, utilities
├── docs/
│   └── architecture/       # System diagrams and design docs
├── prompts/                # Externalized YAML prompt templates
│   ├── agents.yaml         # All agent prompts
│   └── loader.py           # YAML → string renderer
├── infra/terraform/        # IaC deployment stubs (GCP Cloud Run)
├── demo_scenarios/         # Pre-built demo JSON datasets
├── docker-compose.yml      # 6-service container orchestration
└── README.md
```

---

## License

MIT
