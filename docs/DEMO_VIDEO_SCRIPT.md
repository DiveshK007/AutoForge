# Demo Video Script — AutoForge (3 minutes)

## 0:00–0:15 — Hook
"What if six AI agents could autonomously diagnose, fix, and optimize your entire GitLab workflow — while tracking the carbon footprint of every pipeline?"

Show: AutoForge dashboard overview tab with all 6 agents active.

## 0:15–0:45 — The Problem
"Every day, developers waste hours on:
- Debugging CI/CD pipeline failures
- Triaging security vulnerabilities  
- Waiting for code reviews
- And nobody tracks the environmental cost of running thousands of CI pipelines."

Show: A failing pipeline in GitLab. Red X marks.

## 0:45–1:30 — Demo: SRE Agent Fixes a Pipeline
"Watch AutoForge in action. A pipeline fails — missing numpy dependency after a cleanup commit."

1. Show: @mention the AutoForge SRE service account on the failing MR
2. Show: The flow starts (Automate > Sessions shows it running)
3. Show: Agent reads logs, identifies ModuleNotFoundError
4. Show: Agent generates 5 hypotheses with confidence scores
5. Show: Agent creates a fix MR — adds numpy back to requirements.txt
6. Show: The reasoning tree visualization in the dashboard

## 1:30–2:00 — Demo: GreenOps Sustainability Audit
"Now let's audit a pipeline's carbon footprint."

1. Show: @mention the GreenOps service account on a project
2. Show: Agent reads .gitlab-ci.yml, analyzes structure
3. Show: Energy report: X kWh per run, Y kg CO₂, 55/100 efficiency
4. Show: Agent creates optimization MR with parallelized stages
5. Show: GreenOps dashboard tab with carbon savings chart

## 2:00–2:30 — Architecture & Technical Depth
"Under the hood, AutoForge uses a cognitive architecture."

Show: Architecture diagram — perceive → reason → plan → act → reflect

"Each agent generates Tree-of-Thought hypotheses with evidence-weighted 
confidence scores. A DAG orchestrator manages dependencies between agents.
464 tests ensure reliability."

Show: Test suite passing. Dashboard reasoning tree.

## 2:30–2:50 — Security Agent Quick Hit
"The Security Agent scans MRs for vulnerabilities and patches them."

Show: Security flow detecting a lodash CVE, creating a fix MR.

## 2:50–3:00 — Closing
"AutoForge: six AI agents, three custom flows, built on GitLab Duo Agent Platform.
Autonomous DevOps that's fast, safe, and sustainable."

Show: Dashboard with all metrics. GitHub repo link.
