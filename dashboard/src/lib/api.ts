const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* ─── Type Definitions ────────────────────────────────── */

export interface DashboardOverview {
  system_status: string;
  total_workflows: number;
  active_workflows: number;
  success_rate: number;
  agents: AgentSummary[];
  metrics: SystemMetrics;
  meta_intelligence_score: number;
}

export interface AgentSummary {
  name: string;
  type: string;
  status: string;
  tasks_completed: number;
  success_rate: number;
  avg_confidence: number;
}

export interface SystemMetrics {
  success_rate: number;
  avg_fix_time: number;
  avg_confidence: number;
  total_events: number;
  avg_reasoning_depth: number;
  collaboration_index: number;
  self_correction_rate: number;
  carbon_saved_grams: number;
}

export interface Workflow {
  id: string;
  event_type: string;
  status: string;
  created_at: string;
  completed_at?: string;
  tasks: WorkflowTask[];
  timeline: TimelineEntry[];
}

export interface WorkflowTask {
  id: string;
  agent_type: string;
  action: string;
  status: string;
  priority: string;
  result?: Record<string, unknown>;
}

export interface TimelineEntry {
  timestamp: string;
  phase: string;
  agent?: string;
  description: string;
  status: string;
}

export interface ReasoningNode {
  id: string;
  label: string;
  type: string;
  confidence?: number;
  status?: string;
}

export interface ReasoningEdge {
  source: string;
  target: string;
  label?: string;
}

export interface ReasoningVisualization {
  nodes: ReasoningNode[];
  edges: ReasoningEdge[];
}

export interface ActivityEvent {
  timestamp: string;
  type: string;
  agent?: string;
  description: string;
  status: string;
  workflow_id?: string;
}

export interface MetricHistory {
  timestamp: string;
  success_rate: number;
  confidence: number;
  fix_time: number;
  carbon_saved: number;
}

export interface LearningCurve {
  event_number: number;
  success: boolean;
  confidence: number;
  fix_time: number;
  cumulative_success_rate: number;
}

export interface CarbonDashboard {
  carbon_saved_grams: number;
  energy_saved_kwh: number;
  pipeline_efficiency: number;
  optimization_count: number;
  trees_equivalent?: number;
  efficiency_score?: number;
  optimizations?: CarbonOptimization[];
  waste_sources?: WasteSource[];
}

export interface CarbonOptimization {
  suggestion: string;
  estimated_savings_percent: number;
  priority: string;
}

export interface WasteSource {
  source: string;
  waste_percent: number;
}

export interface LearningDashboard {
  learning_curve: LearningCurve[];
  memory_utilization: number;
  knowledge_reuse_count: number;
  reasoning_depth_avg: number;
  meta_intelligence_score: number;
}

/* ─── Fetch Helpers ───────────────────────────────────── */

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/* ─── API Client ──────────────────────────────────────── */

export const api = {
  // Dashboard
  getDashboard: () => fetchAPI<DashboardOverview>('/api/v1/dashboard/overview'),
  getActivityFeed: () => fetchAPI<ActivityEvent[]>('/api/v1/dashboard/activity'),
  getLearningDashboard: () => fetchAPI<LearningDashboard>('/api/v1/dashboard/learning'),
  getCarbonDashboard: () => fetchAPI<CarbonDashboard>('/api/v1/dashboard/carbon'),

  // Agents
  getAgents: () => fetchAPI<AgentSummary[]>('/api/v1/agents/'),
  getAgent: (type: string) => fetchAPI<AgentSummary>(`/api/v1/agents/${type}`),
  getAgentReasoning: (type: string) =>
    fetchAPI<ReasoningVisualization>(`/api/v1/agents/${type}/reasoning`),

  // Workflows
  getWorkflows: () => fetchAPI<Workflow[]>('/api/v1/workflows/'),
  getWorkflow: (id: string) => fetchAPI<Workflow>(`/api/v1/workflows/${id}`),
  getWorkflowTimeline: (id: string) =>
    fetchAPI<TimelineEntry[]>(`/api/v1/workflows/${id}/timeline`),
  getWorkflowReasoning: (id: string) =>
    fetchAPI<ReasoningVisualization>(`/api/v1/workflows/${id}/reasoning`),

  // Telemetry
  getMetrics: () => fetchAPI<SystemMetrics>('/api/v1/telemetry/metrics'),
  getMetricsHistory: () => fetchAPI<MetricHistory[]>('/api/v1/telemetry/metrics/history'),
  getReasoningTrees: () =>
    fetchAPI<Record<string, ReasoningVisualization>>('/api/v1/telemetry/reasoning-trees'),
  getLearningCurve: () => fetchAPI<LearningCurve[]>('/api/v1/telemetry/learning-curve'),

  // Test trigger
  triggerTest: (scenarioName: string) =>
    fetch(`${API_BASE}/api/v1/webhooks/test-trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenarioName }),
    }).then((r) => r.json()),
};
