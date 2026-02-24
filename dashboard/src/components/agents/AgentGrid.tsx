'use client';

import React from 'react';
import { cn, getAgentColor, getAgentIcon, formatPercentage } from '@/lib/utils';
import { StatusBadge } from '@/components/ui/Cards';
import type { AgentSummary } from '@/lib/api';

interface AgentGridProps {
  agents: AgentSummary[];
}

export function AgentGrid({ agents }: AgentGridProps) {
  if (!agents || agents.length === 0) {
    return (
      <div className="text-center py-8 text-surface-200/40">
        <p className="text-4xl mb-2">🤖</p>
        <p>No agents registered yet</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {agents.map((agent) => (
        <AgentCard key={agent.type} agent={agent} />
      ))}
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentSummary }) {
  const color = getAgentColor(agent.type);
  const icon = getAgentIcon(agent.type);

  return (
    <div
      className={cn(
        'glass-card rounded-xl p-4 transition-all duration-300',
        'hover:scale-[1.02] hover:shadow-lg cursor-default'
      )}
      style={{ borderColor: `${color}33` }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">{icon}</span>
          <div>
            <h4 className="text-sm font-semibold text-white">{agent.name}</h4>
            <p className="text-[10px] text-surface-200/50 uppercase tracking-wider">
              {agent.type}
            </p>
          </div>
        </div>
        <StatusBadge status={agent.status} />
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3">
        <div className="text-center">
          <p className="text-lg font-bold" style={{ color }}>
            {agent.tasks_completed}
          </p>
          <p className="text-[10px] text-surface-200/50">Tasks</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold" style={{ color }}>
            {formatPercentage(agent.success_rate)}
          </p>
          <p className="text-[10px] text-surface-200/50">Success</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold" style={{ color }}>
            {formatPercentage(agent.avg_confidence)}
          </p>
          <p className="text-[10px] text-surface-200/50">Confidence</p>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="mt-3">
        <div className="h-1.5 bg-surface-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${agent.avg_confidence * 100}%`,
              backgroundColor: color,
            }}
          />
        </div>
      </div>
    </div>
  );
}
