'use client';

import React from 'react';
import { GlassCard, MetricCard } from '@/components/ui/Cards';
import { CarbonSavingsChart } from '@/components/charts/MetricsCharts';
import type { SystemMetrics, MetricHistory } from '@/lib/api';

interface SustainabilityPanelProps {
  metrics: SystemMetrics | null;
  history: MetricHistory[];
}

export function SustainabilityPanel({ metrics, history }: SustainabilityPanelProps) {
  const carbonSaved = metrics?.carbon_saved_grams || 0;
  const treesEquivalent = (carbonSaved / 21000).toFixed(4); // ~21kg CO2 per tree per year

  return (
    <div className="space-y-4">
      {/* Carbon Headline */}
      <div className="glass-card rounded-xl p-6 text-center" style={{ borderColor: '#22c55e33' }}>
        <p className="text-xs text-emerald-400/60 uppercase tracking-wider mb-2">
          Total Carbon Saved
        </p>
        <div className="flex items-center justify-center gap-3">
          <span className="text-4xl">🌱</span>
          <span className="text-4xl font-bold text-emerald-400 metric-value">
            {carbonSaved.toFixed(2)}g
          </span>
          <span className="text-lg text-surface-200/40">CO₂</span>
        </div>
        <p className="text-xs text-surface-200/40 mt-2">
          Equivalent to {treesEquivalent} trees per year
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label="Efficiency Score"
          value="—"
          icon={<span>⚡</span>}
          color="#22c55e"
        />
        <MetricCard
          label="Optimizations"
          value="0"
          suffix="applied"
          icon={<span>🔄</span>}
          color="#22c55e"
        />
      </div>

      {/* Carbon Chart */}
      <GlassCard title="Carbon Savings Over Time" icon="📈" glowColor="#22c55e">
        <CarbonSavingsChart data={history} />
      </GlassCard>

      {/* Tips */}
      <GlassCard title="Optimization Suggestions" icon="💡" glowColor="#22c55e">
        <div className="space-y-2">
          <SuggestionItem
            text="Parallelize test stages to reduce pipeline duration by ~47%"
            impact="High"
          />
          <SuggestionItem
            text="Enable Docker layer caching for build stages"
            impact="Medium"
          />
          <SuggestionItem
            text="Right-size CI runners based on actual resource usage"
            impact="Medium"
          />
        </div>
      </GlassCard>
    </div>
  );
}

function SuggestionItem({ text, impact }: { text: string; impact: string }) {
  const impactColor =
    impact === 'High'
      ? 'text-emerald-400 bg-emerald-500/10'
      : impact === 'Medium'
      ? 'text-amber-400 bg-amber-500/10'
      : 'text-surface-200/50 bg-surface-700/50';

  return (
    <div className="flex items-start gap-3 p-2.5 rounded-lg bg-surface-800/30">
      <span className="text-emerald-400 mt-0.5">→</span>
      <div className="flex-1">
        <p className="text-xs text-surface-200/70 leading-relaxed">{text}</p>
      </div>
      <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${impactColor}`}>
        {impact}
      </span>
    </div>
  );
}
