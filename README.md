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

| Metric | Formula | What It Measures |
|--------|---------|-----------------|
| Success Rate | Successful Fixes / Total Attempts × 100 | Execution reliability |
| Fix Accuracy | Correct Diagnoses / Total Diagnoses | Reasoning correctness |
| Decision Confidence | Selected Branch Prob / Sum All Probs | Reasoning certainty |
| Reasoning Depth | Explored Branches / Max Branches | Cognitive exploration |
| Learning Rate | (Initial Time - Current Time) / Initial Time × 100 | Autonomy growth |
| Self-Correction Rate | Successful Retries / Failed Attempts | Reflection effectiveness |
| Collaboration Index | Multi-Agent Tasks / Total Tasks | Orchestration depth |
| Carbon Efficiency | (Baseline - Optimized) / Baseline × 100 | Sustainability impact |

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
│   ├── brain/               # Command Brain orchestrator
│   ├── agents/              # Agent workforce
│   ├── integrations/        # GitLab integration layer
│   ├── memory/              # Memory & learning systems
│   ├── telemetry/           # Metrics & observability
│   ├── tools/               # Execution tool gateway
│   └── workflows/           # Workflow definitions
├── dashboard/               # React/Next.js frontend
│   ├── src/
│   │   ├── app/            # Next.js app router
│   │   ├── components/     # UI components
│   │   └── lib/            # Utilities
├── docker-compose.yml       # Container orchestration
└── demo_scenarios/          # Pre-built demo datasets
```

---

## License

MIT
