'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { api } from '@/lib/api';
import type {
  DashboardOverview,
  ActivityEvent,
  MetricHistory,
  LearningCurve,
  ReasoningVisualization,
  CarbonDashboard,
  LearningDashboard,
  RetryEvent,
  CommLink,
} from '@/lib/api';
import { formatPercentage, formatDuration } from '@/lib/utils';

import { GlassCard, MetricCard, StatusBadge } from '@/components/ui/Cards';
import { ErrorBoundary, SafeComponent } from '@/components/ui/ErrorBoundary';
import { OverviewTabSkeleton, MetricsRowSkeleton, GlassCardSkeleton } from '@/components/ui/Skeletons';
import { ThemeProvider, ThemeToggle } from '@/components/ui/ThemeProvider';
import { AgentGrid } from '@/components/agents/AgentGrid';
import { AgentCommGraph, DEMO_COMM_LINKS } from '@/components/agents/AgentCommGraph';
import { ReasoningTree } from '@/components/reasoning/ReasoningTree';
import { MetricsOverTimeChart, LearningCurveChart, CarbonSavingsChart } from '@/components/charts/MetricsCharts';
import { ActivityFeed } from '@/components/activity/ActivityFeed';
import { SustainabilityPanel } from '@/components/sustainability/SustainabilityPanel';
import { DemoTrigger } from '@/components/demo/DemoTrigger';
import { MetaIntelligenceScore } from '@/components/metrics/MetaScore';
import { DAGView } from '@/components/workflows/DAGView';
import { SharedContextView } from '@/components/workflows/SharedContextView';
import { RetryTimeline, RetryBadge } from '@/components/workflows/RetryTimeline';
import { MISBreakdown } from '@/components/metrics/MISBreakdown';
import { useAutoForgeWebSocket } from '@/hooks/useWebSocket';
import { AuthProvider, useAuth } from '@/components/auth/AuthProvider';
import { LoginScreen } from '@/components/auth/LoginScreen';

type Tab = 'overview' | 'agents' | 'reasoning' | 'learning' | 'sustainability' | 'workflows';

export default function DashboardPage() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ErrorBoundary>
          <AuthGate />
        </ErrorBoundary>
      </AuthProvider>
    </ThemeProvider>
  );
}

function AuthGate() {
  const { authenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-950">
        <div className="animate-pulse text-surface-200/50 text-lg">Loading…</div>
      </div>
    );
  }

  if (!authenticated) {
    return <LoginScreen />;
  }

  return <DashboardContent />;
}

function DashboardContent() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [dashboard, setDashboard] = useState<DashboardOverview | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [metricsHistory, setMetricsHistory] = useState<MetricHistory[]>([]);
  const [learningCurve, setLearningCurve] = useState<LearningCurve[]>([]);
  const [reasoning, setReasoning] = useState<ReasoningVisualization | null>(null);
  const [allTrees, setAllTrees] = useState<Record<string, ReasoningVisualization>>({});
  const [selectedTree, setSelectedTree] = useState<string>('');
  const [carbonData, setCarbonData] = useState<CarbonDashboard | null>(null);
  const [learningDash, setLearningDash] = useState<LearningDashboard | null>(null);
  const [retryData, setRetryData] = useState<RetryEvent[]>([]);
  const [commAgents, setCommAgents] = useState<string[]>([]);
  const [commLinks, setCommLinks] = useState<CommLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket for real-time updates
  const { connected: wsConnected, lastMessage } = useAutoForgeWebSocket({
    onMessage: (msg) => {
      const d = msg.data as Record<string, unknown>;

      switch (msg.event) {
        case 'workflow_update': {
          // Optimistically update dashboard workflow counts
          setDashboard((prev) => {
            if (!prev) return prev;
            const status = d.status as string | undefined;
            if (status === 'created') {
              return {
                ...prev,
                total_workflows: prev.total_workflows + 1,
                active_workflows: prev.active_workflows + 1,
              };
            }
            if (status === 'completed' || status === 'failed') {
              return {
                ...prev,
                active_workflows: Math.max(0, prev.active_workflows - 1),
              };
            }
            return prev;
          });
          // Prepend to activity feed
          setActivity((prev) => [
            {
              timestamp: msg.timestamp || new Date().toISOString(),
              type: 'workflow',
              description: `Workflow ${(d.workflow_id as string)?.slice(0, 8)} — ${d.status}`,
              status: d.status as string || 'info',
              workflow_id: d.workflow_id as string,
            },
            ...prev.slice(0, 49),
          ]);
          break;
        }
        case 'agent_action': {
          // Optimistically update the matching agent's stats
          setDashboard((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              agents: prev.agents.map((a) =>
                a.type === d.agent_type
                  ? {
                      ...a,
                      tasks_completed: a.tasks_completed + 1,
                      status: 'active',
                    }
                  : a,
              ),
            };
          });
          // Prepend to activity feed
          setActivity((prev) => [
            {
              timestamp: msg.timestamp || new Date().toISOString(),
              type: 'agent_action',
              agent: d.agent_type as string,
              description: d.detail as string || `${d.agent_type} — ${d.action}`,
              status: (d.success as boolean) ? 'completed' : 'failed',
              workflow_id: d.workflow_id as string,
            },
            ...prev.slice(0, 49),
          ]);
          break;
        }
        case 'activity': {
          setActivity((prev) => [
            {
              timestamp: msg.timestamp || new Date().toISOString(),
              type: d.event as string || 'system',
              agent: d.agent as string,
              description: d.description as string,
              status: d.status as string || 'info',
            },
            ...prev.slice(0, 49),
          ]);
          break;
        }
        case 'metrics_snapshot': {
          // Merge metrics snapshot into dashboard
          const m = d.metrics as Record<string, number> | undefined;
          if (m) {
            setDashboard((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                metrics: { ...prev.metrics, ...m },
              };
            });
          }
          break;
        }
        default:
          break;
      }
    },
  });

  const fetchAll = useCallback(async () => {
    try {
      const [dash, act, hist, learn, reason, carbon, learnDash, retries, comm] = await Promise.allSettled([
        api.getDashboard(),
        api.getActivityFeed(),
        api.getMetricsHistory(),
        api.getLearningCurve(),
        api.getReasoningTrees(),
        api.getCarbonDashboard(),
        api.getLearningDashboard(),
        api.getRetries('latest'),
        api.getAgentCommunication('latest'),
      ]);

      if (dash.status === 'fulfilled') setDashboard(dash.value);
      if (act.status === 'fulfilled') setActivity(act.value);
      if (hist.status === 'fulfilled') setMetricsHistory(hist.value);
      if (learn.status === 'fulfilled') setLearningCurve(learn.value);
      if (carbon.status === 'fulfilled') setCarbonData(carbon.value);
      if (learnDash.status === 'fulfilled') setLearningDash(learnDash.value);
      if (retries.status === 'fulfilled') setRetryData(retries.value.retries || []);
      if (comm.status === 'fulfilled') {
        setCommAgents(comm.value.agents || []);
        setCommLinks(comm.value.links || []);
      }
      if (reason.status === 'fulfilled') {
        const trees = reason.value;
        setAllTrees(trees);
        const firstKey = Object.keys(trees)[0];
        if (firstKey && !selectedTree) {
          setSelectedTree(firstKey);
          setReasoning(trees[firstKey]);
        } else if (selectedTree && trees[selectedTree]) {
          setReasoning(trees[selectedTree]);
        }
      }

      setError(null);
    } catch (err) {
      setError('Failed to connect to AutoForge backend');
    } finally {
      setLoading(false);
    }
  }, [selectedTree]);

  useEffect(() => {
    fetchAll();
    // When WebSocket is connected, slow down polling to a background sync;
    // otherwise fall back to aggressive polling.
    const interval = setInterval(fetchAll, wsConnected ? 30000 : 4000);
    return () => clearInterval(interval);
  }, [fetchAll, wsConnected]);

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'reasoning', label: 'Reasoning', icon: '🧠' },
    { id: 'learning', label: 'Learning', icon: '📈' },
    { id: 'sustainability', label: 'Green', icon: '🌱' },
    { id: 'workflows', label: 'Workflows', icon: '⚡' },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-surface-700/50 bg-surface-900/80 backdrop-blur-lg sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚒️</span>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-brand-400 to-brand-300 bg-clip-text text-transparent">
                AutoForge
              </h1>
              <p className="text-[10px] text-surface-200/40 -mt-0.5">
                Autonomous AI Engineering Orchestrator
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* WebSocket indicator */}
            <div className="flex items-center gap-1.5" aria-label={wsConnected ? 'Real-time connected' : 'Real-time disconnected'}>
              <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-surface-200/30'}`} />
              <span className="text-[10px] text-surface-200/40">{wsConnected ? 'Live' : 'Polling'}</span>
            </div>
            {/* Theme toggle */}
            <ThemeToggle />
            {/* System status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  dashboard?.system_status === 'operational'
                    ? 'bg-emerald-400 animate-pulse-slow'
                    : 'bg-amber-400'
                }`}
                aria-hidden="true"
              />
              <span className="text-xs text-surface-200/60">
                {dashboard?.system_status || 'Connecting...'}
              </span>
            </div>
            {/* MIS Badge */}
            {dashboard && (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-brand-500/30 bg-brand-500/10">
                <span className="text-xs text-brand-300">MIS</span>
                <span className="text-sm font-bold text-brand-400">
                  {(dashboard.meta_intelligence_score ?? 0).toFixed(0)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div className="max-w-[1600px] mx-auto px-6">
          <nav className="flex gap-1 -mb-px" role="tablist" aria-label="Dashboard sections">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`tabpanel-${tab.id}`}
                className={`
                  flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium
                  border-b-2 transition-all duration-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/50 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-900
                  ${
                    activeTab === tab.id
                      ? 'border-brand-400 text-brand-300'
                      : 'border-transparent text-surface-200/50 hover:text-surface-200/80'
                  }
                `}
              >
                <span aria-hidden="true">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-[1600px] mx-auto px-6 py-6" role="main">
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm" role="alert">
            ⚠️ {error} — Make sure the backend is running on port 8000
          </div>
        )}

        {loading && activeTab === 'overview' && <OverviewTabSkeleton />}

        {!loading && activeTab === 'overview' && (
          <SafeComponent fallbackMessage="Overview tab encountered an error">
            <OverviewTab
              dashboard={dashboard}
              activity={activity}
              metricsHistory={metricsHistory}
            />
          </SafeComponent>
        )}

        {activeTab === 'agents' && (
          <SafeComponent fallbackMessage="Agents tab encountered an error">
            <AgentsTab dashboard={dashboard} commAgents={commAgents} commLinks={commLinks} />
          </SafeComponent>
        )}

        {activeTab === 'reasoning' && (
          <SafeComponent fallbackMessage="Reasoning tab encountered an error">
            <ReasoningTab
              reasoning={reasoning}
              allTrees={allTrees}
              selectedTree={selectedTree}
              onSelectTree={(key) => {
                setSelectedTree(key);
                setReasoning(allTrees[key] || null);
              }}
            />
          </SafeComponent>
        )}

        {activeTab === 'learning' && (
          <SafeComponent fallbackMessage="Learning tab encountered an error">
            <LearningTab
              learningCurve={learningCurve}
              metricsHistory={metricsHistory}
              learningDash={learningDash}
            />
          </SafeComponent>
        )}

        {activeTab === 'sustainability' && (
          <SafeComponent fallbackMessage="Sustainability tab encountered an error">
            <SustainabilityTab
              metrics={dashboard?.metrics || null}
              history={metricsHistory}
              carbonData={carbonData}
            />
          </SafeComponent>
        )}

        {activeTab === 'workflows' && (
          <SafeComponent fallbackMessage="Workflows tab encountered an error">
            <WorkflowsTab dashboard={dashboard} retryData={retryData} />
          </SafeComponent>
        )}
      </main>
    </div>
  );
}

/* ─── Tab Components ──────────────────────────────────── */

function OverviewTab({
  dashboard,
  activity,
  metricsHistory,
}: {
  dashboard: DashboardOverview | null;
  activity: ActivityEvent[];
  metricsHistory: MetricHistory[];
}) {
  return (
    <div className="space-y-6">
      {/* Top metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard
          label="Success Rate"
          value={dashboard ? formatPercentage(dashboard.success_rate) : '—'}
          icon={<span>🎯</span>}
          color="#10b981"
          trend="up"
          trendValue="improving"
        />
        <MetricCard
          label="Active Workflows"
          value={dashboard?.active_workflows ?? 0}
          icon={<span>⚡</span>}
          color="#6366f1"
        />
        <MetricCard
          label="Total Workflows"
          value={dashboard?.total_workflows ?? 0}
          icon={<span>📋</span>}
          color="#3b82f6"
        />
        <MetricCard
          label="Avg Confidence"
          value={dashboard?.metrics ? formatPercentage(dashboard.metrics.avg_confidence) : '—'}
          icon={<span>🧠</span>}
          color="#8b5cf6"
        />
        <MetricCard
          label="Self-Correction"
          value={dashboard?.metrics ? formatPercentage(dashboard.metrics.self_correction_rate) : '—'}
          icon={<span>🔄</span>}
          color="#f59e0b"
        />
        <MetricCard
          label="CO₂ Saved"
          value={dashboard?.metrics ? `${dashboard.metrics.carbon_saved_grams.toFixed(1)}g` : '—'}
          icon={<span>🌱</span>}
          color="#22c55e"
        />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Charts + Demo */}
        <div className="lg:col-span-2 space-y-6">
          <GlassCard title="Performance Metrics" icon="📊" subtitle="Success rate & confidence over time">
            <MetricsOverTimeChart data={metricsHistory} />
          </GlassCard>
          <GlassCard title="Demo Control Panel" icon="🎮" subtitle="Trigger demo scenarios to see AutoForge in action">
            <DemoTrigger />
          </GlassCard>
        </div>

        {/* Right: MIS + Activity */}
        <div className="space-y-6">
          <GlassCard title="Intelligence" icon="🧠">
            <MetaIntelligenceScore
              score={dashboard?.meta_intelligence_score ?? 0}
            />
            {dashboard?.metrics && (
              <div className="mt-4 grid grid-cols-2 gap-2">
                <MiniStat label="Reasoning Depth" value={dashboard.metrics.avg_reasoning_depth.toFixed(1)} color="#6366f1" />
                <MiniStat label="Collaboration" value={formatPercentage(dashboard.metrics.collaboration_index)} color="#f59e0b" />
                <MiniStat label="Avg Fix Time" value={formatDuration(dashboard.metrics.avg_fix_time)} color="#3b82f6" />
                <MiniStat label="Events" value={String(dashboard.metrics.total_events)} color="#10b981" />
              </div>
            )}
          </GlassCard>
          <GlassCard title="Activity Feed" icon="📋">
            <div className="max-h-[400px] overflow-y-auto">
              <ActivityFeed events={activity} />
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex flex-col items-center py-2 px-2 rounded-lg bg-surface-800/40">
      <span className="text-lg font-bold metric-value" style={{ color }}>{value}</span>
      <span className="text-[10px] text-surface-200/50 uppercase tracking-wider">{label}</span>
    </div>
  );
}

function AgentsTab({ dashboard, commAgents, commLinks }: { dashboard: DashboardOverview | null; commAgents: string[]; commLinks: CommLink[] }) {
  const agents = dashboard?.agents ?? [];
  const totalTasks = agents.reduce((s, a) => s + a.tasks_completed, 0);
  const avgSuccess = agents.length > 0 ? agents.reduce((s, a) => s + a.success_rate, 0) / agents.length : 0;

  // Use real API data if available, fall back to demo constants
  const graphAgents = commAgents.length > 0 ? commAgents : agents.map(a => a.type);
  const graphLinks = commLinks.length > 0 ? commLinks : DEMO_COMM_LINKS;

  return (
    <div className="space-y-6">
      {/* Agent fleet stats */}
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Total Agents" value={agents.length} icon={<span>🤖</span>} color="#6366f1" />
        <MetricCard label="Total Tasks Completed" value={totalTasks} icon={<span>✅</span>} color="#10b981" />
        <MetricCard label="Fleet Avg Success" value={formatPercentage(avgSuccess)} icon={<span>🎯</span>} color="#f59e0b" />
      </div>

      <GlassCard title="Agent Fleet" icon="🤖" subtitle="6 specialized AI agents — click to explore">
        <AgentGrid agents={agents} />
      </GlassCard>

      {/* Agent Collaboration Matrix */}
      <GlassCard title="Agent Collaboration" icon="🔗" subtitle="Cross-agent knowledge sharing patterns">
        <CollaborationMatrix agents={agents} />
      </GlassCard>

      {/* Agent Communication Graph — wired to real API data */}
      <SafeComponent fallbackMessage="Communication graph could not be loaded">
        <GlassCard title="Agent Communication Flow" icon="🔀" subtitle="Real-time data flow between agents via shared context bus">
          <AgentCommGraph
            agents={graphAgents}
            links={graphLinks}
          />
        </GlassCard>
      </SafeComponent>
    </div>
  );
}

function CollaborationMatrix({ agents }: { agents: { type: string; name: string }[] }) {
  const types = agents.map(a => a.type);
  // Demo collaboration strengths
  const strengths: Record<string, Record<string, number>> = {
    sre: { security: 0.85, qa: 0.72, greenops: 0.68, review: 0.45, docs: 0.55 },
    security: { sre: 0.85, qa: 0.78, review: 0.62, greenops: 0.40, docs: 0.50 },
    qa: { sre: 0.72, security: 0.78, review: 0.70, docs: 0.65, greenops: 0.55 },
    review: { qa: 0.70, security: 0.62, docs: 0.80, sre: 0.45, greenops: 0.35 },
    docs: { review: 0.80, qa: 0.65, sre: 0.55, security: 0.50, greenops: 0.42 },
    greenops: { sre: 0.68, qa: 0.55, docs: 0.42, security: 0.40, review: 0.35 },
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="p-2 text-left text-surface-200/50"></th>
            {types.map(t => (
              <th key={t} className="p-2 text-center text-surface-200/60 uppercase tracking-wider">{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {types.map(row => (
            <tr key={row}>
              <td className="p-2 text-surface-200/60 uppercase tracking-wider font-semibold">{row}</td>
              {types.map(col => {
                if (row === col) {
                  return <td key={col} className="p-2 text-center"><span className="text-surface-200/20">—</span></td>;
                }
                const strength = strengths[row]?.[col] ?? 0;
                const opacity = Math.max(0.1, strength);
                const bg = strength > 0.7 ? '#10b981' : strength > 0.5 ? '#f59e0b' : '#6b7280';
                return (
                  <td key={col} className="p-2 text-center">
                    <div
                      className="inline-flex items-center justify-center w-10 h-7 rounded text-[10px] font-bold"
                      style={{ backgroundColor: `${bg}${Math.round(opacity * 40).toString(16).padStart(2, '0')}`, color: bg }}
                    >
                      {(strength * 100).toFixed(0)}%
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReasoningTab({
  reasoning,
  allTrees,
  selectedTree,
  onSelectTree,
}: {
  reasoning: ReasoningVisualization | null;
  allTrees: Record<string, ReasoningVisualization>;
  selectedTree: string;
  onSelectTree: (key: string) => void;
}) {
  const treeKeys = Object.keys(allTrees);
  const scenarioLabels: Record<string, string> = {
    pipeline_failure: '💥 Pipeline Failure',
    security_vulnerability: '🛡️ Security Vulnerability',
    merge_request_opened: '📝 Merge Request',
    inefficient_pipeline: '🌱 Inefficient Pipeline',
  };

  return (
    <div className="space-y-6">
      {/* Scenario selector */}
      {treeKeys.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {treeKeys.map(key => (
            <button
              key={key}
              onClick={() => onSelectTree(key)}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 border ${
                selectedTree === key
                  ? 'bg-brand-500/20 border-brand-500/50 text-brand-300'
                  : 'glass-card border-white/10 text-surface-200/60 hover:text-surface-200/80 hover:border-brand-400/30'
              }`}
            >
              {scenarioLabels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </button>
          ))}
        </div>
      )}

      {/* Main reasoning tree */}
      <GlassCard
        title="Reasoning Tree Visualizer"
        icon="🧠"
        subtitle={selectedTree ? `Scenario: ${scenarioLabels[selectedTree] || selectedTree}` : 'Interactive visualization of agent thought process'}
      >
        <div className="h-[600px]">
          <ReasoningTree data={reasoning} />
        </div>
      </GlassCard>

      {/* Reasoning legend */}
      <GlassCard title="Node Types" icon="🎨" subtitle="Each node represents a cognitive step">
        <div className="flex flex-wrap gap-3">
          {[
            { type: 'event', color: '#f59e0b', label: 'Event Trigger' },
            { type: 'perception', color: '#3b82f6', label: 'Perception' },
            { type: 'hypothesis', color: '#8b5cf6', label: 'Hypothesis' },
            { type: 'reasoning', color: '#6366f1', label: 'Reasoning' },
            { type: 'plan', color: '#10b981', label: 'Plan' },
            { type: 'action', color: '#ef4444', label: 'Action' },
            { type: 'reflection', color: '#ec4899', label: 'Reflection' },
            { type: 'result', color: '#22c55e', label: 'Result' },
          ].map(item => (
            <div key={item.type} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-surface-800/40">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-xs text-surface-200/70">{item.label}</span>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Stats from selected tree */}
      {reasoning && reasoning.nodes && reasoning.nodes.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Nodes" value={reasoning.nodes.length} icon={<span>🔵</span>} color="#6366f1" />
          <MetricCard label="Edges" value={reasoning.edges.length} icon={<span>🔗</span>} color="#3b82f6" />
          <MetricCard
            label="Avg Confidence"
            value={formatPercentage(
              reasoning.nodes.reduce((s, n) => s + (n.confidence ?? 0), 0) / reasoning.nodes.length
            )}
            icon={<span>🎯</span>}
            color="#10b981"
          />
          <MetricCard
            label="Hypotheses"
            value={reasoning.nodes.filter(n => n.type === 'hypothesis').length}
            icon={<span>💡</span>}
            color="#f59e0b"
          />
        </div>
      )}
    </div>
  );
}

function LearningTab({
  learningCurve,
  metricsHistory,
  learningDash,
}: {
  learningCurve: LearningCurve[];
  metricsHistory: MetricHistory[];
  learningDash: LearningDashboard | null;
}) {
  return (
    <div className="space-y-6">
      {/* Top stats */}
      {learningDash && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="MIS Score"
            value={learningDash.meta_intelligence_score.toFixed(1)}
            icon={<span>🧠</span>}
            color="#6366f1"
          />
          <MetricCard
            label="Memory Utilization"
            value={formatPercentage(learningDash.memory_utilization)}
            icon={<span>💾</span>}
            color="#3b82f6"
          />
          <MetricCard
            label="Knowledge Reuse"
            value={learningDash.knowledge_reuse_count}
            suffix="times"
            icon={<span>♻️</span>}
            color="#10b981"
          />
          <MetricCard
            label="Reasoning Depth"
            value={learningDash.reasoning_depth_avg.toFixed(1)}
            suffix="avg steps"
            icon={<span>🔍</span>}
            color="#f59e0b"
          />
        </div>
      )}

      {/* MIS Breakdown */}
      {learningDash && (
        <GlassCard title="Meta-Intelligence Score Breakdown" icon="🧠" subtitle="5-factor weighted intelligence assessment">
          <MISBreakdown
            accuracy={0.926}
            learning={0.73}
            reflection={0.34}
            collaboration={0.78}
            sustainability={0.85}
            overall={(learningDash.meta_intelligence_score ?? 0) / 100}
          />
        </GlassCard>
      )}

      {/* Learning curve */}
      <GlassCard title="Learning Curve" icon="📈" subtitle="How the system improves over time — confidence & success rate">
        <LearningCurveChart data={learningCurve} />
      </GlassCard>

      {/* Performance trends */}
      <GlassCard title="Performance Trends" icon="📊" subtitle="Metrics evolution over processing history">
        <MetricsOverTimeChart data={metricsHistory} />
      </GlassCard>
    </div>
  );
}

function SustainabilityTab({
  metrics,
  history,
  carbonData,
}: {
  metrics: DashboardOverview['metrics'] | null;
  history: MetricHistory[];
  carbonData: CarbonDashboard | null;
}) {
  return (
    <div className="space-y-6">
      {/* Enhanced sustainability panel */}
      <SustainabilityPanel metrics={metrics} history={history} carbonData={carbonData} />
    </div>
  );
}

function WorkflowsTab({ dashboard, retryData }: { dashboard: DashboardOverview | null; retryData: RetryEvent[] }) {
  // Example DAG tasks for visualization
  const demoTasks = [
    { task_id: 'sre-1', agent_type: 'sre', action: 'diagnose root cause', status: 'completed', dependencies: [] },
    { task_id: 'greenops-1', agent_type: 'greenops', action: 'energy audit', status: 'completed', dependencies: [] },
    { task_id: 'security-1', agent_type: 'security', action: 'scan fix for CVEs', status: 'completed', dependencies: ['sre-1'] },
    { task_id: 'qa-1', agent_type: 'qa', action: 'generate tests', status: 'completed', dependencies: ['sre-1'] },
    { task_id: 'review-1', agent_type: 'review', action: 'review fix quality', status: 'completed', dependencies: ['security-1', 'qa-1'] },
    { task_id: 'docs-1', agent_type: 'docs', action: 'update changelog', status: 'running', dependencies: ['review-1'] },
  ];

  const demoSharedContext: Record<string, Record<string, unknown>> = {
    sre: { root_cause: 'missing numpy dependency', fix_branch: 'autoforge/fix-pipeline-abc123', confidence: 0.92, fix_description: 'Re-add numpy>=1.24.0 to requirements.txt' },
    security: { scan_result: 'clean', cve_count: 0, validation: 'Fix introduces no new vulnerabilities' },
    qa: { tests_generated: 3, coverage_delta: '+4.2%', test_files: ['test_numpy_import.py', 'test_data_processing.py'] },
    greenops: { energy_kwh: 0.0108, carbon_kg: 0.000005, efficiency_score: 85 },
  };

  // Use real retry data from API if available, fall back to demo retries
  const fallbackRetries: RetryEvent[] = [
    { attempt: 1, maxAttempts: 3, agent: 'sre', strategy: 'Original diagnosis — missing dependency', outcome: 'failure', confidence: 0.45, duration_ms: 1200 },
    { attempt: 2, maxAttempts: 3, agent: 'sre', strategy: 'Alternate fix — pin exact version numpy==1.24.4', outcome: 'failure', confidence: 0.62, duration_ms: 800 },
    { attempt: 3, maxAttempts: 3, agent: 'sre', strategy: 'Reflection-based — update requirements.txt with range constraint', outcome: 'success', confidence: 0.91, duration_ms: 950 },
  ];
  const retries = retryData.length > 0 ? retryData : fallbackRetries;

  return (
    <div className="space-y-6">
      {/* DAG Execution View */}
      <GlassCard title="Task DAG Execution" icon="🔀" subtitle="Dependency-ordered wave execution — agents run in parallel when possible">
        <DAGView tasks={demoTasks} />
      </GlassCard>

      {/* Shared Context + Workflow History */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title="Shared Context Bus" icon="🔗" subtitle="Cross-agent data flow — agents publish & consume results">
          <SharedContextView context={demoSharedContext} />
        </GlassCard>

        <GlassCard title="Workflow Summary" icon="⚡">
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-surface-200/60">
              <span>Total Processed</span>
              <span className="text-white font-bold">{dashboard?.total_workflows ?? 0}</span>
            </div>
            <div className="flex items-center justify-between text-xs text-surface-200/60">
              <span>Active Now</span>
              <span className="text-brand-400 font-bold">{dashboard?.active_workflows ?? 0}</span>
            </div>
            <div className="flex items-center justify-between text-xs text-surface-200/60">
              <span>Success Rate</span>
              <span className="text-emerald-400 font-bold">{dashboard ? formatPercentage(dashboard.success_rate) : '—'}</span>
            </div>
            <div className="flex items-center justify-between text-xs text-surface-200/60">
              <span>Agents in Fleet</span>
              <span className="text-white font-bold">{dashboard?.agents?.length ?? 6}</span>
            </div>
            <div className="mt-4 p-3 rounded-lg bg-brand-500/10 border border-brand-500/20">
              <p className="text-xs text-brand-300/80 leading-relaxed">
                💡 AutoForge orchestrates tasks as a DAG (Directed Acyclic Graph).
                Independent tasks run in parallel waves, while dependent tasks wait
                for upstream results via the shared context bus.
              </p>
            </div>
          </div>
        </GlassCard>
      </div>

      <GlassCard title="Demo Control Panel" icon="🎮" subtitle="Trigger a scenario to watch the full pipeline">
        <DemoTrigger />
      </GlassCard>

      {/* Retry Visualization — wired to real API data */}
      <GlassCard title="Self-Correction Timeline" icon="🔄" subtitle="Agent retry and escalation history">
        <RetryTimeline retries={retries} />
      </GlassCard>
    </div>
  );
}
