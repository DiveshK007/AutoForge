'use client';

import React from 'react';
import { GlassCard, MetricCard } from '@/components/ui/Cards';
import { CarbonSavingsChart } from '@/components/charts/MetricsCharts';
import type { SystemMetrics, MetricHistory, CarbonDashboard } from '@/lib/api';
import { formatPercentage } from '@/lib/utils';

interface SustainabilityPanelProps {
  metrics: SystemMetrics | null;
  history: MetricHistory[];
  carbonData?: CarbonDashboard | null;
}

export function SustainabilityPanel({ metrics, history, carbonData }: SustainabilityPanelProps) {
  const carbonSaved = carbonData?.carbon_saved_grams ?? metrics?.carbon_saved_grams ?? 0;
  const treesEquivalent = carbonData?.trees_equivalent ?? (carbonSaved / 21000);
  const efficiencyScore = carbonData?.efficiency_score ?? 0;
  const pipelineEfficiency = carbonData?.pipeline_efficiency ?? 0;
  const optimizationCount = carbonData?.optimization_count ?? 0;
  const energySaved = carbonData?.energy_saved_kwh ?? 0;

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
          Equivalent to {treesEquivalent.toFixed(4)} trees per year
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Efficiency Score"
          value={efficiencyScore > 0 ? `${efficiencyScore}%` : '—'}
          icon={<span>⚡</span>}
          color="#22c55e"
        />
        <MetricCard
          label="Optimizations"
          value={optimizationCount}
          suffix="applied"
          icon={<span>🔄</span>}
          color="#22c55e"
        />
        <MetricCard
          label="Pipeline Efficiency"
          value={pipelineEfficiency > 0 ? `${pipelineEfficiency.toFixed(1)}%` : '—'}
          icon={<span>🚀</span>}
          color="#10b981"
        />
        <MetricCard
          label="Energy Saved"
          value={energySaved > 0 ? `${(energySaved * 1000).toFixed(1)}Wh` : '—'}
          icon={<span>🔋</span>}
          color="#10b981"
        />
      </div>

      {/* Carbon Chart */}
      <GlassCard title="Carbon Savings Over Time" icon="📈" glowColor="#22c55e">
        <CarbonSavingsChart data={history} />
      </GlassCard>

      {/* Optimization Suggestions from backend */}
      {carbonData?.optimizations && carbonData.optimizations.length > 0 && (
        <GlassCard title="AI-Generated Optimization Suggestions" icon="💡" glowColor="#22c55e">
          <div className="space-y-2">
            {carbonData.optimizations.map((opt, i) => (
              <SuggestionItem
                key={i}
                text={opt.suggestion}
                impact={opt.priority === 'critical' ? 'Critical' : opt.priority === 'high' ? 'High' : 'Medium'}
                savings={opt.estimated_savings_percent}
              />
            ))}
          </div>
        </GlassCard>
      )}

      {/* Fallback suggestions */}
      {(!carbonData?.optimizations || carbonData.optimizations.length === 0) && (
        <GlassCard title="Optimization Suggestions" icon="💡" glowColor="#22c55e">
          <div className="space-y-2">
            <SuggestionItem text="Parallelize test stages to reduce pipeline duration by ~47%" impact="High" />
            <SuggestionItem text="Enable Docker layer caching for build stages" impact="Medium" />
            <SuggestionItem text="Right-size CI runners based on actual resource usage" impact="Medium" />
          </div>
        </GlassCard>
      )}

      {/* Waste Sources */}
      {carbonData?.waste_sources && carbonData.waste_sources.length > 0 && (
        <GlassCard title="Identified Waste Sources" icon="🗑️" glowColor="#f59e0b">
          <div className="space-y-2">
            {carbonData.waste_sources.map((ws, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-surface-800/30">
                <span className="text-amber-400 shrink-0">⚠️</span>
                <div className="flex-1">
                  <p className="text-xs text-surface-200/70">{ws.source}</p>
                </div>
                <div className="shrink-0">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-amber-400/70"
                        style={{ width: `${ws.waste_percent}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-amber-400 font-bold w-8 text-right">
                      {ws.waste_percent}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  );
}

function SuggestionItem({ text, impact, savings }: { text: string; impact: string; savings?: number }) {
  const impactColor =
    impact === 'Critical'
      ? 'text-red-400 bg-red-500/10'
      : impact === 'High'
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
      <div className="flex items-center gap-2 shrink-0">
        {savings !== undefined && (
          <span className="text-[10px] text-emerald-400 font-bold">~{savings}%</span>
        )}
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${impactColor}`}>
          {impact}
        </span>
      </div>
    </div>
  );
}
