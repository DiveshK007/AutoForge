# AutoForge — Memory & Learning Architecture

## Memory Layers

```
┌────────────────────────────────────────────────────┐
│                 Memory Store                        │
│                                                    │
│  Layer 1: Episodic Memory                          │
│  ┌──────────────────────────────────────────────┐  │
│  │  Raw experiences: what happened, when, where  │  │
│  │  Indexed by: agent_type, failure_type, time   │  │
│  │  Retention: unlimited (append-only)           │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  Layer 2: Skill Library                            │
│  ┌──────────────────────────────────────────────┐  │
│  │  Abstracted capabilities per agent            │  │
│  │  use_count, avg_confidence, avg_fix_time      │  │
│  │  Grows with experience                        │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  Layer 3: Semantic Patterns                        │
│  ┌──────────────────────────────────────────────┐  │
│  │  Abstract patterns from concrete episodes     │  │
│  │  "dependency issues" ← "numpy missing"        │  │
│  │  Enables generalisation across projects       │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  Layer 4: Cross-Agent Knowledge                    │
│  ┌──────────────────────────────────────────────┐  │
│  │  Skills shared from one agent to all others   │  │
│  │  SRE fixes → shared with QA, Security, etc.   │  │
│  │  Builds collective intelligence               │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  Layer 5: Policy Learning                          │
│  ┌──────────────────────────────────────────────┐  │
│  │  Tracks policy violations and overrides       │  │
│  │  Identifies frequently-blocked actions        │  │
│  │  Feeds back into agent behaviour              │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

## Learning Curve

The system tracks improvement over time:

```
Confidence ▲
           │     ╭──────────────────
     0.9   │    ╱
     0.8   │   ╱
     0.7   │  ╱
     0.6   │ ╱
     0.5   │╱
           └──────────────────────→ Time
           t0    t1    t2    t3
```

Each data point captures:
- Timestamp
- Agent type
- Confidence score
- Cumulative success rate
- Experience count

## Meta-Intelligence Score (MIS)

Weighted composite of 5 factors:

```
MIS = Accuracy     × 0.30    # (completed / total) workflows
    + Learning     × 0.25    # Confidence improvement over time
    + Reflection   × 0.20    # Self-correction rate
    + Collaboration × 0.15   # Multi-agent workflow ratio
    + Sustainability × 0.10  # Energy efficiency (lower = better)
```
