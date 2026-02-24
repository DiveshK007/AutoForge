# AutoForge — Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     GitLab Webhooks (Events)                        │
│  pipeline_failure │ security_alert │ MR_opened │ MR_merged          │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Gateway (:8000)                          │
│  POST /api/webhook/gitlab     POST /api/webhook/test-trigger       │
│  Token validation │ Event normalisation │ Rate limiting              │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CommandBrain (Orchestrator)                     │
│  ┌───────────┐  ┌───────────────┐  ┌───────────────────────────┐   │
│  │  Router    │→ │ Decomposer    │→ │  DAG Executor (Waves)     │   │
│  │(event→agt)│  │(event→tasks+  │  │  Wave 0: independent      │   │
│  │           │  │  dependencies) │  │  Wave 1: depends on W0    │   │
│  └───────────┘  └───────────────┘  │  Wave N: ...               │   │
│                                     └──────────┬────────────────┘   │
│  ┌───────────┐  ┌───────────────┐              │                   │
│  │  Policy   │  │  Conflict     │              │                   │
│  │  Engine   │  │  Resolver     │←─────────────┘                   │
│  └───────────┘  └───────────────┘                                   │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
          ┌────────────┼────────────────────┐
          ▼            ▼                    ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │               Multi-Agent Workforce                               │
  │  ┌─────┐ ┌──────────┐ ┌────┐ ┌────────┐ ┌──────┐ ┌──────────┐  │
  │  │ SRE │ │ Security │ │ QA │ │ Review │ │ Docs │ │ GreenOps │  │
  │  └──┬──┘ └────┬─────┘ └─┬──┘ └───┬────┘ └──┬───┘ └────┬─────┘  │
  │     │         │          │        │          │          │         │
  │  Each agent follows: Perceive → Reason → Plan → Act → Reflect   │
  └──────┬────────┬──────────┬────────┬──────────┬─────────┬─────────┘
         │        │          │        │          │         │
         ▼        ▼          ▼        ▼          ▼         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                    Shared Context Bus                              │
  │  workflow.publish_context(agent, key, value)                      │
  │  workflow.consume_context(agent_type=None)                        │
  │  Enables cross-agent data flow within a single workflow           │
  └──────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                  Intelligence Substrate                            │
  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
  │  │ Memory Store│  │ Telemetry    │  │ Reasoning Engine       │   │
  │  │  - Episodes │  │  - MIS Score │  │  - Claude Sonnet 4     │   │
  │  │  - Skills   │  │  - Fix Time  │  │  - 4 frameworks        │   │
  │  │  - Semantic │  │  - Carbon    │  │  - Extended thinking   │   │
  │  │  - Sharing  │  │  - Learning  │  │  - Multi-depth trees   │   │
  │  │  - Policies │  │  - Activity  │  │                        │   │
  │  └─────────────┘  └──────────────┘  └────────────────────────┘   │
  └──────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │               Next.js Dashboard (:3000)                           │
  │  Overview │ Agents │ Reasoning │ Memory │ Green │ Activity       │
  │  React Flow reasoning trees │ Recharts metrics │ 3s polling      │
  └──────────────────────────────────────────────────────────────────┘
```

## Agent Cognitive Pipeline

Every agent follows the same 5-phase loop:

```
┌──────────┐     ┌──────────┐     ┌──────┐     ┌─────┐     ┌──────────┐
│ Perceive │ ──→ │  Reason  │ ──→ │ Plan │ ──→ │ Act │ ──→ │ Reflect  │
│          │     │          │     │      │     │     │     │          │
│ Gather   │     │ Hypothe- │     │ Best │     │ API │     │ Success? │
│ context, │     │ sis tree │     │ fix  │     │ ops │     │ Learn    │
│ logs,    │     │ Evidence │     │ plan │     │     │     │ skills   │
│ signals  │     │ weighting│     │      │     │     │     │          │
└──────────┘     └──────────┘     └──────┘     └─────┘     └──────────┘
```

## DAG Execution Waves

Tasks are grouped into waves based on dependency resolution:

```
Event: pipeline_failure

Wave 0 (no deps):   [ SRE (diagnose) ]  [ GreenOps (audit) ]
                          │
                          ▼
Wave 1 (dep: SRE):  [ Security (validate) ]  [ QA (test) ]  [ Docs (changelog) ]
```

## Data Flow

```
GitLab Webhook
     │
     ▼
NormalizedEvent ──→ TaskDecomposer ──→ AgentTask[] (with DAG)
                                           │
                                    ┌──────┴──────┐
                                    ▼              ▼
                               Wave 0 tasks   Wave 1 tasks ...
                                    │              │
                                    ▼              ▼
                              Agent.execute()  Agent.execute()
                                    │              │
                                    ▼              ▼
                              Shared Context Bus (cross-agent)
                                    │
                                    ▼
                              Memory Store (episodic + semantic + shared)
                                    │
                                    ▼
                              Telemetry (MIS, learning, carbon)
                                    │
                                    ▼
                              Dashboard API ──→ React Frontend
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| DEMO_MODE toggle | Deterministic live demos without LLM calls |
| DAG over queue | Respects causal ordering (SRE must diagnose before QA can test the fix) |
| Shared context bus | Agents share findings in-workflow without global state |
| Evidence weighting | `prob×0.5 + log_match×0.3 + hist_success×0.2` — combines prior, empirical, and learned factors |
| Depth-2 reasoning trees | Sub-hypotheses for fix and alternative per top hypothesis |
| Policy guardrails | Branch protection, diff limits, rate limits — safe-by-default |
| Semantic memory | Abstract patterns from concrete episodes → generalise across projects |
| Cross-agent knowledge sharing | SRE's dep-fix skill is shared with QA/Security for awareness |
| 5-factor MIS | Accuracy, Learning, Reflection, Collaboration, Sustainability |
