# AutoForge — Agent Interaction Protocol

## Inter-Agent Communication

Agents communicate through two mechanisms:

### 1. Shared Context Bus (Synchronous, In-Workflow)
```python
# SRE publishes its findings
workflow.publish_context("sre", "root_cause", "missing numpy dependency")
workflow.publish_context("sre", "fix_branch", "autoforge/fix-pipeline-abc123")

# Security consumes SRE's context when it runs (Wave 1)
sre_context = workflow.consume_context("sre")
# → {"root_cause": "missing numpy dependency", "fix_branch": "autoforge/fix-..."}
```

### 2. Memory Store (Asynchronous, Cross-Workflow)
```python
# After SRE fixes a dependency issue
experience = AgentExperience(
    agent_type="sre",
    failure_type="pipeline_failure",
    action_taken="add_dependency",
    reusable_skill="dependency_restoration",
    success=True,
)
await memory.store_experience(experience)
# → Skill extracted, shared with security/qa agents
# → Semantic pattern built for future recall
```

## Dependency Graph Per Event Type

### pipeline_failure
```
SRE ──────────→ Security
  │──────────→ QA
  │──────────→ Docs
GreenOps (independent)
```

### security_alert
```
Security ─────→ SRE
  │───────────→ QA
```

### merge_request_opened
```
Review ────────→ QA
Security (independent)
```

### merge_request_merged
```
Docs (independent)
GreenOps (independent)
```

## Escalation Protocol

```
Task fails
  │
  ├─→ Retry (same agent, fresh attempt)
  │     │
  │     └─→ Fails again
  │           │
  │           ├─→ Alternate agent (if available)
  │           │     │
  │           │     └─→ Fails again
  │           │           │
  │           │           └─→ Manual Review (human escalation)
  │           │
  │           └─→ No alternate → Manual Review
  │
  └─→ Succeeds → Reflect → Learn
```
