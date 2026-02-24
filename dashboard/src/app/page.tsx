'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { api } from '@/lib/api';
import type {
  DashboardOverview,
  ActivityEvent,
  MetricHistory,
  LearningCurve,
  ReasoningVisualization,
} from '@/lib/api';
import { formatPercentage, formatDuration } from '@/lib/utils';

import { GlassCard, MetricCard, StatusBadge } from '@/components/ui/Cards';
import { AgentGrid } from '@/components/agents/AgentGrid';
import { ReasoningTree } from '@/components/reasoning/ReasoningTree';
import { MetricsOverTimeChart, LearningCurveChart } from '@/components/charts/MetricsCharts';
import { ActivityFeed } from '@/components/activity/ActivityFeed';
import { SustainabilityPanel } from '@/components/sustainability/SustainabilityPanel';
import { DemoTrigger } from '@/components/demo/DemoTrigger';
import { MetaIntelligenceScore } from '@/components/metrics/MetaScore';

type Tab = 'overview' | 'agents' | 'reasoning' | 'learning' | 'sustainability' | 'workflows';

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [dashboard, setDashboard] = useState<DashboardOverview | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [metricsHistory, setMetricsHistory] = useState<MetricHistory[]>([]);
  const [learningCurve, setLearningCurve] = useState<LearningCurve[]>([]);
  const [reasoning, setReasoning] = useState<ReasoningVisualization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [dash, act, hist, learn, reason] = await Promise.allSettled([
        api.getDashboard(),
        api.getActivityFeed(),
        api.getMetricsHistory(),
        api.getLearningCurve(),
        api.getReasoningTrees(),
      ]);

      if (dash.status === 'fulfilled') setDashboard(dash.value);
      if (act.status === 'fulfilled') setActivity(act.value);
      if (hist.status === 'fulfilled') setMetricsHistory(hist.value);
      if (learn.status === 'fulfilled') setLearningCurve(learn.value);
      if (reason.status === 'fulfilled') {
        const trees = reason.value;
        const firstKey = Object.keys(trees)[0];
        if (firstKey) setReasoning(trees[firstKey]);
      }

      setError(null);
    } catch (err) {
      setError('Failed to connect to AutoForge backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 3000);
    return () => clearInterval(interval);
  }, [fetchAll]);

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
            {/* System status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  dashboard?.system_status === 'operational'
                    ? 'bg-emerald-400 animate-pulse-slow'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-xs text-surface-200/60">
                {dashboard?.system_status || 'Connecting...'}
              </span>
            </div>
          </div>
        </div>

        {/* Tab bar */}
        <div className="max-w-[1600px] mx-auto px-6">
          <nav className="flex gap-1 -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium
                  border-b-2 transition-all duration-200
                  ${
                    activeTab === tab.id
                      ? 'border-brand-400 text-brand-300'
                      : 'border-transparent text-surface-200/50 hover:text-surface-200/80'
                  }
                `}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-[1600px] mx-auto px-6 py-6">
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
            ⚠️ {error} — Make sure the backend is running on port 8000
          </div>
        )}

        {activeTab === 'overview' && (
          <OverviewTab
            dashboard={dashboard}
            activity={activity}
            metricsHistory={metricsHistory}
          />
        )}

        {activeTab === 'agents' && (
          <AgentsTab dashboard={dashboard} />
        )}

        {activeTab === 'reasoning' && (
          <ReasoningTab reasoning={reasoning} />
        )}

        {activeTab === 'learning' && (
          <LearningTab
            learningCurve={learningCurve}
            metricsHistory={metricsHistory}
          />
        )}

        {activeTab === 'sustainability' && (
          <SustainabilityTab
            metrics={dashboard?.metrics || null}
            history={metricsHistory}
          />
        )}

        {activeTab === 'workflows' && (
          <WorkflowsTab dashboard={dashboard} />
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
          <GlassCard title="Performance Metrics" icon="📊">
            <MetricsOverTimeChart data={metricsHistory} />
          </GlassCard>
          <GlassCard title="Demo Control Panel" icon="🎮">
            <DemoTrigger />
          </GlassCard>
        </div>

        {/* Right: MIS + Activity */}
        <div className="space-y-6">
          <GlassCard title="Intelligence" icon="🧠">
            <MetaIntelligenceScore
              score={dashboard?.meta_intelligence_score ?? 0}
            />
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

function AgentsTab({ dashboard }: { dashboard: DashboardOverview | null }) {
  return (
    <div className="space-y-6">
      <GlassCard title="Agent Fleet" icon="🤖" subtitle="6 specialized AI agents">
        <AgentGrid agents={dashboard?.agents ?? []} />
      </GlassCard>
    </div>
  );
}

function ReasoningTab({
  reasoning,
}: {
  reasoning: ReasoningVisualization | null;
}) {
  return (
    <div className="space-y-6">
      <GlassCard title="Reasoning Tree Visualizer" icon="🧠" subtitle="Interactive visualization of agent thought process">
        <div className="h-[600px]">
          <ReasoningTree data={reasoning} />
        </div>
      </GlassCard>
    </div>
  );
}

function LearningTab({
  learningCurve,
  metricsHistory,
}: {
  learningCurve: LearningCurve[];
  metricsHistory: MetricHistory[];
}) {
  return (
    <div className="space-y-6">
      <GlassCard title="Learning Curve" icon="📈" subtitle="How the system improves over time">
        <LearningCurveChart data={learningCurve} />
      </GlassCard>
      <GlassCard title="Metrics History" icon="📊" subtitle="Performance trends">
        <MetricsOverTimeChart data={metricsHistory} />
      </GlassCard>
    </div>
  );
}

function SustainabilityTab({
  metrics,
  history,
}: {
  metrics: DashboardOverview['metrics'] | null;
  history: MetricHistory[];
}) {
  return (
    <div className="space-y-6">
      <SustainabilityPanel metrics={metrics} history={history} />
    </div>
  );
}

function WorkflowsTab({ dashboard }: { dashboard: DashboardOverview | null }) {
  return (
    <div className="space-y-6">
      <GlassCard title="Workflow History" icon="⚡">
        <div className="text-center py-8 text-surface-200/40">
          <p className="text-3xl mb-2">⚡</p>
          <p className="text-sm">
            {(dashboard?.total_workflows ?? 0) > 0
              ? `${dashboard!.total_workflows} workflows processed`
              : 'No workflows yet — trigger a demo scenario to start'}
          </p>
        </div>
      </GlassCard>

      <GlassCard title="Demo Control Panel" icon="🎮">
        <DemoTrigger />
      </GlassCard>
    </div>
  );
}
