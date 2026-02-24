#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  AutoForge — Full-Stack Testing Script
#  Run this to verify backend + dashboard + all integrations work correctly
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

API="http://localhost:8000"
DASH="http://localhost:3000"
PASS=0
FAIL=0
TOTAL=0

green()  { printf "\033[0;32m%s\033[0m" "$1"; }
red()    { printf "\033[0;31m%s\033[0m" "$1"; }
yellow() { printf "\033[0;33m%s\033[0m" "$1"; }
bold()   { printf "\033[1m%s\033[0m" "$1"; }

check() {
  local label="$1"
  local result="$2"
  TOTAL=$((TOTAL + 1))
  if [ "$result" = "true" ]; then
    PASS=$((PASS + 1))
    echo "  $(green '✅') $label"
  else
    FAIL=$((FAIL + 1))
    echo "  $(red '❌') $label"
  fi
}

section() {
  echo ""
  bold "━━━ $1 ━━━"
  echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
bold "⚒️  AutoForge Full-Stack Test Suite"
echo "    $(date)"
echo ""

# ─── 1. Check services are running ──────────────────────────────────────────
section "1. Service Health"

BACKEND_UP=$(curl -sf "$API/health" > /dev/null 2>&1 && echo true || echo false)
check "Backend running on :8000" "$BACKEND_UP"

if [ "$BACKEND_UP" != "true" ]; then
  echo ""
  red "  ⚠ Backend is not running! Start it with:"
  echo ""
  echo "    cd backend && uvicorn main:app --port 8000 --reload"
  echo ""
  echo "  Skipping all API tests."
  echo ""
  echo "Results: $PASS/$TOTAL passed, $FAIL failed"
  exit 1
fi

DASHBOARD_UP=$(curl -sf "$DASH" > /dev/null 2>&1 && echo true || echo false)
check "Dashboard running on :3000" "$DASHBOARD_UP"

HEALTH=$(curl -sf "$API/health")
check "Health status = operational" "$(echo "$HEALTH" | python3 -c 'import json,sys; print("true" if json.load(sys.stdin).get("status")=="operational" else "false")' 2>/dev/null || echo false)"
check "Health system = AutoForge" "$(echo "$HEALTH" | python3 -c 'import json,sys; print("true" if json.load(sys.stdin).get("system")=="AutoForge" else "false")' 2>/dev/null || echo false)"

# ─── 2. Dashboard Overview ──────────────────────────────────────────────────
section "2. Dashboard Overview (/api/v1/dashboard/overview)"

OVERVIEW=$(curl -sf "$API/api/v1/dashboard/overview")
check "Returns 200" "$([ -n "$OVERVIEW" ] && echo true || echo false)"
check "Has system_status" "$(echo "$OVERVIEW" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if "system_status" in d else "false")' 2>/dev/null || echo false)"
check "Has agents array (≥6)" "$(echo "$OVERVIEW" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if len(d.get("agents",[])) >= 6 else "false")' 2>/dev/null || echo false)"
check "Has metrics object" "$(echo "$OVERVIEW" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if isinstance(d.get("metrics"), dict) else "false")' 2>/dev/null || echo false)"
check "Has meta_intelligence_score" "$(echo "$OVERVIEW" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if 0 <= d.get("meta_intelligence_score",0) <= 100 else "false")' 2>/dev/null || echo false)"
check "success_rate > 0.8" "$(echo "$OVERVIEW" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("success_rate",0) > 0.8 else "false")' 2>/dev/null || echo false)"
check "total_workflows > 0" "$(echo "$OVERVIEW" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("total_workflows",0) > 0 else "false")' 2>/dev/null || echo false)"
check "metrics.carbon_saved_grams > 0" "$(echo "$OVERVIEW" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("metrics",{}).get("carbon_saved_grams",0) > 0 else "false")' 2>/dev/null || echo false)"

# ─── 3. Agent Fleet ─────────────────────────────────────────────────────────
section "3. Agent Fleet (/api/v1/dashboard/agents)"

AGENTS=$(curl -sf "$API/api/v1/dashboard/agents")
check "Returns 200" "$([ -n "$AGENTS" ] && echo true || echo false)"
check "Has agents + count" "$(echo "$AGENTS" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if "agents" in d and "count" in d else "false")' 2>/dev/null || echo false)"
check "6 agents present" "$(echo "$AGENTS" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("count") == 6 else "false")' 2>/dev/null || echo false)"
check "Agent types: sre,security,qa,review,docs,greenops" "$(echo "$AGENTS" | python3 -c '
import json,sys
d=json.load(sys.stdin)
types = {a["type"] for a in d.get("agents",[])}
expected = {"sre","security","qa","review","docs","greenops"}
print("true" if expected == types else "false")
' 2>/dev/null || echo false)"

# ─── 4. Activity Feed ───────────────────────────────────────────────────────
section "4. Activity Feed (/api/v1/dashboard/activity)"

ACTIVITY=$(curl -sf "$API/api/v1/dashboard/activity")
check "Returns flat array" "$(echo "$ACTIVITY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if isinstance(d, list) else "false")' 2>/dev/null || echo false)"
check "Has ≥5 items" "$(echo "$ACTIVITY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if len(d) >= 5 else "false")' 2>/dev/null || echo false)"
check "Items have timestamp,type,description,status" "$(echo "$ACTIVITY" | python3 -c '
import json,sys
d=json.load(sys.stdin)
item = d[0] if d else {}
print("true" if all(k in item for k in ["timestamp","type","description","status"]) else "false")
' 2>/dev/null || echo false)"
check "/activity-feed returns same data" "$([ "$(curl -sf "$API/api/v1/dashboard/activity")" = "$(curl -sf "$API/api/v1/dashboard/activity-feed")" ] && echo true || echo false)"

# ─── 5. Reasoning Trees ─────────────────────────────────────────────────────
section "5. Reasoning Trees"

TREES=$(curl -sf "$API/api/v1/telemetry/reasoning-trees")
check "/reasoning-trees returns dict" "$(echo "$TREES" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if isinstance(d, dict) else "false")' 2>/dev/null || echo false)"
check "4 scenario keys present" "$(echo "$TREES" | python3 -c '
import json,sys
d=json.load(sys.stdin)
expected = {"pipeline_failure","security_vulnerability","merge_request_opened","inefficient_pipeline"}
print("true" if expected.issubset(set(d.keys())) else "false")
' 2>/dev/null || echo false)"
check "Each tree has nodes + edges" "$(echo "$TREES" | python3 -c '
import json,sys
d=json.load(sys.stdin)
ok = all("nodes" in t and "edges" in t and len(t["nodes"]) >= 5 for t in d.values())
print("true" if ok else "false")
' 2>/dev/null || echo false)"

# Test individual reasoning endpoint
for scenario in pipeline_failure security_vulnerability merge_request_opened inefficient_pipeline; do
  R=$(curl -sf "$API/api/v1/dashboard/reasoning/$scenario")
  check "/reasoning/$scenario → nodes + edges" "$(echo "$R" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if "nodes" in d and "edges" in d else "false")' 2>/dev/null || echo false)"
done

# Test alias resolution
R_ALIAS=$(curl -sf "$API/api/v1/dashboard/reasoning/pipeline_failure_missing_dep")
check "/reasoning/pipeline_failure_missing_dep (alias) → 200" "$([ -n "$R_ALIAS" ] && echo true || echo false)"

# Node types span full chain
check "Node types cover full chain (event→result)" "$(echo "$TREES" | python3 -c '
import json,sys
d=json.load(sys.stdin)
tree = list(d.values())[0]
types = {n["type"] for n in tree["nodes"]}
expected = {"event","perception","hypothesis","reasoning","plan","action","reflection","result"}
print("true" if expected.issubset(types) else "false")
' 2>/dev/null || echo false)"

# ─── 6. Learning Dashboard ──────────────────────────────────────────────────
section "6. Learning (/api/v1/dashboard/learning)"

LEARNING=$(curl -sf "$API/api/v1/dashboard/learning")
check "Returns 200" "$([ -n "$LEARNING" ] && echo true || echo false)"
check "Has learning_curve array (≥10 items)" "$(echo "$LEARNING" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if len(d.get("learning_curve",[])) >= 10 else "false")' 2>/dev/null || echo false)"
check "Has meta_intelligence_score" "$(echo "$LEARNING" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if 0 <= d.get("meta_intelligence_score",0) <= 100 else "false")' 2>/dev/null || echo false)"
check "Has memory_utilization" "$(echo "$LEARNING" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if 0 <= d.get("memory_utilization",0) <= 1 else "false")' 2>/dev/null || echo false)"
check "Has knowledge_reuse_count" "$(echo "$LEARNING" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("knowledge_reuse_count",0) > 0 else "false")' 2>/dev/null || echo false)"

# ─── 7. Carbon / Sustainability ─────────────────────────────────────────────
section "7. Carbon Dashboard (/api/v1/dashboard/carbon)"

CARBON=$(curl -sf "$API/api/v1/dashboard/carbon")
check "Returns 200" "$([ -n "$CARBON" ] && echo true || echo false)"
check "carbon_saved_grams > 0" "$(echo "$CARBON" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("carbon_saved_grams",0) > 0 else "false")' 2>/dev/null || echo false)"
check "efficiency_score 0–100" "$(echo "$CARBON" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if 0 <= d.get("efficiency_score",0) <= 100 else "false")' 2>/dev/null || echo false)"
check "Has optimizations array" "$(echo "$CARBON" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if len(d.get("optimizations",[])) >= 2 else "false")' 2>/dev/null || echo false)"
check "Optimizations have suggestion+savings+priority" "$(echo "$CARBON" | python3 -c '
import json,sys
d=json.load(sys.stdin)
ok = all(all(k in o for k in ["suggestion","estimated_savings_percent","priority"]) for o in d.get("optimizations",[]))
print("true" if ok else "false")
' 2>/dev/null || echo false)"
check "Has waste_sources array" "$(echo "$CARBON" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if len(d.get("waste_sources",[])) >= 1 else "false")' 2>/dev/null || echo false)"

# ─── 8. Telemetry Endpoints ─────────────────────────────────────────────────
section "8. Telemetry Endpoints"

METRICS=$(curl -sf "$API/api/v1/telemetry/metrics")
check "/metrics → system_metrics + agent_metrics + learning_metrics + sustainability_metrics" "$(echo "$METRICS" | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("true" if all(k in d for k in ["system_metrics","agent_metrics","learning_metrics","sustainability_metrics"]) else "false")
' 2>/dev/null || echo false)"

HISTORY=$(curl -sf "$API/api/v1/telemetry/metrics/history")
check "/metrics/history → flat array (≥5 items)" "$(echo "$HISTORY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if isinstance(d, list) and len(d) >= 5 else "false")' 2>/dev/null || echo false)"
check "/metrics/history items have timestamp,success_rate,confidence" "$(echo "$HISTORY" | python3 -c '
import json,sys
d=json.load(sys.stdin)
item = d[0]
print("true" if all(k in item for k in ["timestamp","success_rate","confidence","fix_time","carbon_saved"]) else "false")
' 2>/dev/null || echo false)"

CURVE=$(curl -sf "$API/api/v1/telemetry/learning-curve")
check "/learning-curve → flat array (≥15 items)" "$(echo "$CURVE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if isinstance(d, list) and len(d) >= 15 else "false")' 2>/dev/null || echo false)"

for ep in success-rate fix-time collaboration reasoning-depth memory-reuse; do
  R=$(curl -sf "$API/api/v1/telemetry/metrics/$ep")
  check "/metrics/$ep → 200" "$([ -n "$R" ] && echo true || echo false)"
done

# ─── 9. Webhook Test Trigger ────────────────────────────────────────────────
section "9. Webhook Test Trigger (/api/v1/webhooks/test-trigger)"

TRIGGER=$(curl -sf -X POST "$API/api/v1/webhooks/test-trigger" -H "Content-Type: application/json" -d '{"scenario":"pipeline_failure_missing_dep"}')
check "Trigger returns status=triggered" "$(echo "$TRIGGER" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("status")=="triggered" else "false")' 2>/dev/null || echo false)"
check "Trigger maps scenario → event_type=pipeline_failure" "$(echo "$TRIGGER" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("event_type")=="pipeline_failure" else "false")' 2>/dev/null || echo false)"
check "Trigger returns workflow_id" "$(echo "$TRIGGER" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("workflow_id","") != "" else "false")' 2>/dev/null || echo false)"

TRIGGER2=$(curl -sf -X POST "$API/api/v1/webhooks/test-trigger" -H "Content-Type: application/json" -d '{"scenario":"security_vulnerability"}')
check "security_vulnerability → security_alert" "$(echo "$TRIGGER2" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("event_type")=="security_alert" else "false")' 2>/dev/null || echo false)"

TRIGGER3=$(curl -sf -X POST "$API/api/v1/webhooks/test-trigger" -H "Content-Type: application/json" -d '{}')
check "Empty body → defaults to pipeline_failure" "$(echo "$TRIGGER3" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("true" if d.get("event_type")=="pipeline_failure" else "false")' 2>/dev/null || echo false)"

# ─── 10. Agent API ──────────────────────────────────────────────────────────
section "10. Agent API (/api/v1/agents/)"

AGENT_LIST=$(curl -sf "$API/api/v1/agents/")
check "Returns agent list" "$(echo "$AGENT_LIST" | python3 -c '
import json,sys
d=json.load(sys.stdin)
agents = d.get("agents", d) if isinstance(d, dict) else d
print("true" if isinstance(agents, (list, dict)) and len(agents) >= 5 else "false")
' 2>/dev/null || echo false)"

# ─── 11. Dashboard Frontend ─────────────────────────────────────────────────
section "11. Dashboard Frontend"

if [ "$DASHBOARD_UP" = "true" ]; then
  DASH_HTML=$(curl -sf "$DASH")
  check "Dashboard HTML loads" "$([ -n "$DASH_HTML" ] && echo true || echo false)"
  check "Contains 'AutoForge' title" "$(echo "$DASH_HTML" | grep -qi 'autoforge' && echo true || echo false)"
  check "Contains Next.js chunks" "$(echo "$DASH_HTML" | grep -q '_next' && echo true || echo false)"
else
  echo "  $(yellow '⏭')  Dashboard not running — skipping frontend tests"
fi

# ─── 12. Data Integrity Checks ──────────────────────────────────────────────
section "12. Data Integrity"

check "Metrics history is chronologically ordered" "$(echo "$HISTORY" | python3 -c '
import json,sys
d=json.load(sys.stdin)
ts = [x["timestamp"] for x in d]
print("true" if ts == sorted(ts) else "false")
' 2>/dev/null || echo false)"

check "Learning curve is ordered by event_number" "$(echo "$CURVE" | python3 -c '
import json,sys
d=json.load(sys.stdin)
nums = [x["event_number"] for x in d]
print("true" if nums == sorted(nums) else "false")
' 2>/dev/null || echo false)"

check "All agents have success_rate ∈ [0,1]" "$(echo "$OVERVIEW" | python3 -c '
import json,sys
d=json.load(sys.stdin)
ok = all(0 <= a["success_rate"] <= 1 for a in d.get("agents",[]))
print("true" if ok else "false")
' 2>/dev/null || echo false)"

check "All agents have avg_confidence ∈ [0,1]" "$(echo "$OVERVIEW" | python3 -c '
import json,sys
d=json.load(sys.stdin)
ok = all(0 <= a["avg_confidence"] <= 1 for a in d.get("agents",[]))
print("true" if ok else "false")
' 2>/dev/null || echo false)"

# ═══════════════════════════════════════════════════════════════════════════════
#  Results
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$FAIL" -eq 0 ]; then
  echo ""
  echo "  $(green "🎉 ALL $TOTAL TESTS PASSED!") AutoForge is running perfectly."
  echo ""
else
  echo ""
  echo "  $(green "✅ $PASS passed")  $(red "❌ $FAIL failed")  (Total: $TOTAL)"
  echo ""
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Backend:    $API"
echo "  Dashboard:  $DASH"
echo "  Swagger:    $API/docs"
echo ""
