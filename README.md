# 🔥 AutoForge — Autonomous AI Engineering Orchestrator for GitLab

> Six AI agents that autonomously diagnose, fix, secure, test, review, and optimize your GitLab projects — with built-in sustainability tracking.

**Built on the GitLab Duo Agent Platform for the [GitLab AI Hackathon](https://gitlab.devpost.com/).**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-464%20passing-brightgreen)](#-testing)
[![GitLab Duo](https://img.shields.io/badge/GitLab%20Duo-Agent%20Platform-orange)](https://docs.gitlab.com/user/duo_agent_platform/)

### 🏆 Prize Targeting
| Category | Our Angle |
|----------|-----------|
| **Grand Prize** ($15K) | Multi-agent orchestration + cognitive reasoning + GreenOps |
| **Most Technically Impressive** ($5K) | Tree-of-thought reasoning, DAG workflows, 464 tests |
| **Green Agent Prize** ($3K) | GreenOps energy/carbon auditing + pipeline optimization |
| **Sustainable Design Bonus** ($500×4) | Energy-efficient architecture choices |
| **GitLab & Anthropic** ($10K) | Claude-powered reasoning via GitLab Duo |
| **Most Impactful** ($5K) | Solves real pipeline failure, security, and sustainability pain |

---

## 🧠 What is AutoForge?

AutoForge is an event-driven, multi-agent DevOps automation platform built on the **GitLab Duo Agent Platform**. It uses Claude (via GitLab Duo) to reason over software lifecycle signals and autonomously execute remediation, validation, documentation, and optimization workflows.

### GitLab Duo Agent Platform Integration

AutoForge registers as **3 custom flows** and **3 custom agents** on GitLab Duo:

| Flow/Agent | Type | What It Does |
|------------|------|-------------|
| 🛠 SRE Pipeline Fix | Flow (4 components) | Perceive → Reason → Act → Reflect on pipeline failures |
| 🔐 Security Vulnerability Fix | Flow (3 components) | Scan → Assess → Patch security issues |
| 🌱 GreenOps Sustainability Audit | Flow (3 components) | Audit → Analyze → Optimize for energy efficiency |
| 🛠 SRE Agent | Custom Agent | Interactive pipeline diagnosis via Duo Chat |
| 🔐 Security Agent | Custom Agent | Interactive security review via Duo Chat |
| 🌱 GreenOps Agent | Custom Agent | Interactive sustainability audit via Duo Chat |

See [`gitlab_duo/`](gitlab_duo/) for all flow YAML configs and agent system prompts.

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
┌─────────────────────────────────────────────────────────────────────┐
│                     GitLab Webhooks (Events)                        │
│  pipeline_failure │ security_alert │ MR_opened │ MR_merged          │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              FastAPI Gateway (:8000) + JWT Auth                      │
│  POST /webhooks/gitlab   POST /auth/token   GET /dashboard/*       │
│  Token validation │ Rate limiting │ Correlation IDs                  │
└────────────┬────────────────────────────────────────────────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌──────────┐  ┌──────────────────────────────────────────────────────┐
│  Celery  │  │            CommandBrain (Orchestrator)                │
│  Worker  │  │  Router → Decomposer → DAG Executor (Waves)          │
│  Queue   │  │  Policy Engine │ Conflict Resolver │ Retry/Escalate  │
└──────────┘  └──────────┬───────────────────────────────────────────┘
                         │
          ┌──────────────┼────────────────────┐
          ▼              ▼                    ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │               Multi-Agent Workforce (6 Agents)                    │
  │  Each: Perceive → Reason → Plan → Act → Reflect → Learn          │
  │  Claude Sonnet 4 │ Depth-2 reasoning trees │ Evidence weighting  │
  └──────────┬───────────────────────────────────────────────────────┘
             │
             ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │              Shared Context Bus + Memory Store                    │
  │  PostgreSQL (experiences, skills, workflows, policies)            │
  │  Redis (caching layer) │ In-memory (fast fallback)               │
  │  5 layers: Episodic │ Skills │ Semantic │ Cross-Agent │ Policy   │
  └──────────┬───────────────────────────────────────────────────────┘
             │
             ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │           Next.js Dashboard (:3000) — 6 Tabs                     │
  │  Overview │ Agents │ Reasoning │ Workflows │ Green │ Activity    │
  │  React Flow graphs │ Recharts │ Real-time API polling             │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (tested on 3.11 – 3.14)
- Node.js 18+
- Docker & Docker Compose (for full stack)
- GitLab account with API token (production mode)
- Anthropic API key (production mode)

### Option A: Docker Compose (Recommended)

```bash
git clone https://github.com/DiveshK007/AutoForge.git
cd AutoForge
cp .env.example .env          # Edit with your API keys
docker-compose up -d           # Starts 6 services
```

Services:
| Service | Port | Description |
|---------|------|-------------|
| Backend | :8000 | FastAPI + Swagger at `/docs` |
| Dashboard | :3000 | Next.js UI |
| Worker | — | Celery task processor |
| Redis | :6379 | Cache + Celery broker |
| PostgreSQL | :5432 | Persistent memory |
| ChromaDB | :8100 | Vector store |

### Option B: Local Development

```bash
# Backend
cd backend
python -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements-full.txt
uvicorn main:app --reload --port 8000

# Dashboard (new terminal)
cd dashboard
npm install && npm run dev
```

### Option C: One-Command Dev

```bash
make dev    # Starts backend + dashboard in parallel
```

### Configure GitLab Webhook

Point your GitLab project webhook to:
```
https://your-domain/api/v1/webhooks/gitlab
```

Events: Pipeline events • Merge request events • Push events

---

## 🔐 Authentication

AutoForge supports **real JWT authentication** in production and transparent demo-mode passthrough.

```bash
# Get a token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Use the token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/dashboard/overview
```

Roles: `admin` (full access) • `operator` (trigger + view) • `viewer` (read-only)

In `DEMO_MODE=true`, all endpoints accept the demo API key automatically.

---

## 💾 Persistence Layer

AutoForge uses a **graceful-degradation** architecture — every component works without external services, automatically upgrading when infrastructure is available.

| Layer | Technology | Fallback |
|-------|-----------|----------|
| Primary DB | PostgreSQL + SQLAlchemy async | In-memory dicts |
| Cache | Redis | Skip (direct DB or memory) |
| Task Queue | Celery + Redis broker | In-process asyncio |
| Vector Store | ChromaDB | Pattern matching |

### Database Schema (5 tables)

```
experiences      — Agent learning history (per fix attempt)
skills           — Abstracted reusable capabilities
workflows        — Execution state + retry history + shared context
workflow_tasks   — Individual agent tasks within a workflow DAG
policy_events    — Violations and human overrides for policy learning
```

Migrations managed by **Alembic**:
```bash
cd backend
alembic upgrade head              # Apply migrations
alembic revision --autogenerate -m "add new table"  # Generate new migration
```

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

**Retry & Escalation**: Failed tasks retry with exponential backoff → escalate to alternate agent → flag for manual review. Full retry history is tracked and exposed via API.

---

## 📊 Telemetry & Meta-Intelligence

### Meta-Intelligence Score (MIS) — Weighted 5-Factor Formula

```
MIS = Accuracy × 0.30 + Learning × 0.25 + Reflection × 0.20 + Collaboration × 0.15 + Sustainability × 0.10
```

| Metric | Weight | What It Measures |
|--------|--------|-----------------|
| Accuracy | 30% | Completed / Total Workflows |
| Learning | 25% | Confidence Improvement Over Time |
| Reflection | 20% | Self-Corrections / Failed Attempts |
| Collaboration | 15% | Multi-Agent Workflows / Total |
| Sustainability | 10% | Energy Efficiency Score |

### Dashboard Tabs

| Tab | Contents |
|-----|----------|
| **Overview** | System status, MIS score, agent fleet, recent activity |
| **Agents** | Per-agent metrics, communication graph (React Flow) |
| **Reasoning** | Interactive reasoning trees with hypothesis exploration |
| **Workflows** | DAG visualization, shared context, retry timeline |
| **Green** | Carbon savings, pipeline optimizations, waste sources |
| **Activity** | Real-time event feed with filtering |

---

## 🛡️ Safety Guardrails

| Guardrail | Description |
|-----------|-------------|
| Branch Protection | Agents cannot push to `main`, `master`, `production`, `release`, `staging` |
| Diff Size Limits | Maximum 500 lines per merge request |
| High-Risk Actions | `force_push`, `delete_branch`, `drop_database`, etc. require human approval |
| Escalation Protocol | Retry → Alternate Agent → Manual Review |
| Policy Learning | Tracks violations and adapts agent behaviour |
| Rate Limiting | Per-IP request throttling with configurable limits |
| Correlation IDs | Every request traced end-to-end |

---

## 🎮 DEMO_MODE

Set `DEMO_MODE=true` (default) for **deterministic live demos without LLM API calls or external services**.

Precomputed reasoning trees cover 4 scenarios:
- `pipeline_failure` — Missing numpy dependency diagnosis + fix
- `security_vulnerability` — SQL injection detection + patch
- `merge_request_opened` — Code review + test generation
- `inefficient_pipeline` — GreenOps carbon optimization

All 6 agents produce realistic outputs. The dashboard is fully interactive.

```bash
# Trigger a demo scenario
curl -X POST http://localhost:8000/api/v1/webhooks/test-trigger \
  -H "Content-Type: application/json" \
  -d '{"scenario": "pipeline_failure_missing_dep"}'
```

---

## 🧠 Agent Cognition Pipeline

Every agent follows the same 5-phase cognitive architecture:

```
Perception → Reasoning → Planning → Tool Execution → Reflection → Memory Encoding
```

Each agent generates:
- **Structured hypotheses** with evidence-weighted confidence scores
- **Depth-2 reasoning trees** exploring multiple fix strategies
- **Risk-scored alternatives** ranked by likelihood and impact
- **Reflection summaries** recording what worked and what didn't
- **Reusable skill patterns** extracted from successful fixes

---

## 🧪 Testing

**464 tests** — all passing.

| Suite | Count | What It Covers |
|-------|-------|----------------|
| Core | 30 | Models, brain, memory, telemetry |
| API | 10 | Endpoint contracts, auth |
| Dashboard Demo | 69 | All demo data shapes, API response formats |
| Enterprise | 47 | Logging, middleware, auth, tracing, schemas |
| Full Implementation | 82 | DB layer, JWT, Celery, retry/comm APIs, persistence |
| Integration Layer | 100 | GitLab client, services, tools, webhook processing |
| Integration (bash) | 62 | Full-stack end-to-end via HTTP |
| Audit Gap | 51 | Vector store, persistent workflows, HMAC, approvals |
| Production Readiness | 35 | RBAC, CORS, auth middleware |
| **Total** | **464** | |

```bash
# Run all pytest tests
make test
# or:
PYTHONPATH=backend pytest backend/tests/ -v

# Run integration tests (requires running services)
bash test_autoforge.sh
```

---

## 📡 API Endpoints

### Core
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness probe (checks brain, memory, telemetry) |
| POST | `/api/v1/webhooks/gitlab` | GitLab webhook receiver |
| POST | `/api/v1/webhooks/test-trigger` | Demo scenario trigger |

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/token` | Issue JWT token |
| GET | `/api/v1/auth/me` | Introspect current auth |

### Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dashboard/overview` | System overview + MIS score |
| GET | `/api/v1/dashboard/agents` | Agent fleet status |
| GET | `/api/v1/dashboard/activity` | Activity feed |
| GET | `/api/v1/dashboard/workflows` | Workflow list |
| GET | `/api/v1/dashboard/reasoning/{scenario}` | Reasoning tree visualization |
| GET | `/api/v1/dashboard/learning` | Learning curve data |
| GET | `/api/v1/dashboard/carbon` | Carbon/sustainability metrics |
| GET | `/api/v1/dashboard/retries/{workflow_id}` | Retry history for a workflow |
| GET | `/api/v1/dashboard/communication/{workflow_id}` | Agent communication graph |
| GET | `/api/v1/dashboard/explain/{workflow_id}` | Human-readable workflow explanation |

### Telemetry
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/telemetry/metrics` | Full metrics bundle |
| GET | `/api/v1/telemetry/metrics/history` | Historical metrics |
| GET | `/api/v1/telemetry/learning-curve` | Learning progression |
| GET | `/api/v1/telemetry/metrics/success-rate` | Success rate breakdown |
| GET | `/api/v1/telemetry/metrics/fix-time` | Fix time analysis |
| GET | `/api/v1/telemetry/metrics/collaboration` | Collaboration metrics |
| GET | `/api/v1/telemetry/metrics/reasoning-depth` | Reasoning depth stats |
| GET | `/api/v1/telemetry/metrics/memory-reuse` | Memory reuse metrics |

Full Swagger docs at `http://localhost:8000/docs`

---

## 📁 Project Structure

```
AutoForge/
├── backend/                    # FastAPI backend (14,700+ lines Python)
│   ├── main.py                # App entry + lifespan + middleware stack
│   ├── config.py              # Settings (env vars, DEMO_MODE, thresholds)
│   ├── worker.py              # Celery worker (async agent task execution)
│   ├── brain/                 # Command Brain orchestrator
│   │   ├── orchestrator.py    # DAG wave executor + retry/escalation + history
│   │   ├── task_decomposer.py # Event → DAG tasks with dependency wiring
│   │   ├── router.py          # Event → agent routing rules
│   │   ├── policy_engine.py   # Branch protection, diff limits, guardrails
│   │   └── conflict_resolver.py
│   ├── agents/                # 6-agent workforce
│   │   ├── base_agent.py      # 5-phase cognitive pipeline
│   │   ├── reasoning_engine.py # Claude Sonnet 4 + extended thinking
│   │   ├── sre/               # SRE: diagnosis, evidence weighting, depth-2 trees
│   │   ├── security/          # Security: CVE analysis, vulnerability scanning
│   │   ├── qa/                # QA: test generation, regression detection
│   │   ├── review/            # Review: code review, architecture analysis
│   │   ├── docs/              # Docs: changelog, API docs, README updates
│   │   └── greenops/          # GreenOps: carbon scoring, pipeline optimization
│   ├── api/                   # FastAPI route handlers
│   │   ├── dashboard.py       # 15+ dashboard endpoints
│   │   ├── webhooks.py        # GitLab webhook + Celery dispatch
│   │   ├── auth.py            # JWT token issuance + introspection
│   │   └── explain.py         # Human-readable workflow explanations
│   ├── db/                    # Database persistence layer
│   │   ├── engine.py          # SQLAlchemy async engine + session factory
│   │   ├── tables.py          # ORM models (5 tables)
│   │   ├── repository.py      # CRUD with graceful degradation
│   │   └── redis_cache.py     # Redis cache with auto-fallback
│   ├── alembic/               # Database migrations
│   │   ├── env.py             # Migration environment config
│   │   └── versions/          # Migration scripts (0001_initial_schema)
│   ├── memory/                # Memory & learning (5 layers)
│   │   └── store.py           # PostgreSQL + Redis + in-memory fallback
│   ├── middleware/             # Enterprise middleware
│   │   ├── auth.py            # JWT verification + demo-mode passthrough
│   │   ├── rate_limiter.py    # Per-IP rate limiting
│   │   └── correlation.py     # Request correlation IDs
│   ├── integrations/          # GitLab API client layer
│   │   └── gitlab/            # Auth, retry, rate limit, services, models
│   ├── demo/                  # DEMO_MODE precomputed data
│   │   └── engine.py          # 4 scenarios × 6 agents
│   ├── models/                # Pydantic data models
│   ├── telemetry/             # Metrics + observability
│   ├── tools/                 # Execution tool gateway
│   ├── workflows/             # Event-specific workflow definitions
│   └── tests/                 # 378 tests (7 test files)
│       ├── test_core.py
│       ├── test_api.py
│       ├── test_dashboard_demo.py
│       ├── test_audit_improvements.py
│       ├── test_enterprise_improvements.py
│       ├── test_full_implementation.py
│       └── test_integration_layer.py
├── dashboard/                  # Next.js 14 frontend (3,350+ lines TSX)
│   └── src/
│       ├── app/page.tsx       # 6-tab dashboard
│       ├── components/        # 9 component directories
│       └── lib/api.ts         # Typed API client
├── docs/architecture/          # Design docs (ARCHITECTURE, MEMORY, AGENTS)
├── gitlab_duo/                 # GitLab Duo Agent Platform configs
│   ├── agents/                # System prompts for custom agents
│   │   ├── sre_agent_prompt.md
│   │   ├── security_agent_prompt.md
│   │   └── greenops_agent_prompt.md
│   └── flows/                 # Flow Registry v1 YAML configs
│       ├── autoforge_sre_flow.yaml
│       ├── autoforge_security_flow.yaml
│       └── autoforge_greenops_flow.yaml
├── prompts/                    # YAML prompt templates
├── infra/terraform/            # IaC stubs (GCP Cloud Run)
├── .github/workflows/ci.yml   # CI: tests, lint, Docker build, security scan
├── docker-compose.yml          # 6-service orchestration
├── Dockerfile                  # Backend + worker image
├── Dockerfile.dashboard        # Dashboard image
├── Makefile                    # Dev commands
├── AGENTS.md                   # GitLab Duo agent behavior config
├── LICENSE                     # MIT License
├── test_autoforge.sh           # 62-test integration suite
└── pyproject.toml              # Python project config
```

---

## 🏆 Hackathon Prize Targeting

AutoForge targets multiple prize categories in the [GitLab AI Hackathon](https://gitlab.devpost.com/):

| Prize | Amount | Our Differentiator |
|-------|--------|-------------------|
| Grand Prize | $15,000 | Multi-agent DAG orchestration + autonomous remediation + 464 tests |
| Most Technically Impressive | $5,000 | Tree-of-thought reasoning, evidence-weighted hypotheses, cognitive pipeline |
| Green Agent Prize | $3,000 | GreenOps energy/carbon auditing with real kWh/CO₂ calculations |
| Sustainable Design Bonus | $500×4 | Energy-efficient pipeline optimization, conservative estimates |
| GitLab & Anthropic | $10,000 | Claude-powered reasoning engine via GitLab Duo Agent Platform |
| Most Impactful | $5,000 | Solves real DevOps pain: pipeline failures, security vulns, sustainability |

### GitLab Duo Agent Platform Artifacts

```
gitlab_duo/
├── agents/
│   ├── sre_agent_prompt.md        # SRE Agent system prompt
│   ├── security_agent_prompt.md   # Security Agent system prompt
│   └── greenops_agent_prompt.md   # GreenOps Agent system prompt
└── flows/
    ├── autoforge_sre_flow.yaml         # Pipeline Fix flow (v1 YAML)
    ├── autoforge_security_flow.yaml    # Vulnerability Fix flow (v1 YAML)
    └── autoforge_greenops_flow.yaml    # Sustainability Audit flow (v1 YAML)
```

---

## License

MIT
