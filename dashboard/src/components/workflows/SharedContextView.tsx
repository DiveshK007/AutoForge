'use client';

import React from 'react';
import { getAgentColor, getAgentIcon } from '@/lib/utils';

interface SharedContextEntry {
  agent_type: string;
  data: Record<string, unknown>;
}

interface SharedContextViewProps {
  context: Record<string, Record<string, unknown>>;
}

export function SharedContextView({ context }: SharedContextViewProps) {
  const entries: SharedContextEntry[] = Object.entries(context || {}).map(
    ([agent_type, data]) => ({ agent_type, data: data as Record<string, unknown> })
  );

  if (entries.length === 0) {
    return (
      <div className="text-center py-4 text-surface-200/40">
        <p className="text-sm">No shared context yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
        <span className="text-xs font-semibold uppercase tracking-wider text-brand-400">
          Shared Context Bus
        </span>
      </div>

      {/* Flow arrows between agents */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {entries.map((entry, i) => (
          <React.Fragment key={entry.agent_type}>
            <div
              className="flex items-center gap-1 px-3 py-1.5 rounded-full border"
              style={{
                borderColor: getAgentColor(entry.agent_type),
                backgroundColor: `${getAgentColor(entry.agent_type)}15`,
              }}
            >
              <span className="text-sm">{getAgentIcon(entry.agent_type)}</span>
              <span
                className="text-xs font-bold uppercase"
                style={{ color: getAgentColor(entry.agent_type) }}
              >
                {entry.agent_type}
              </span>
            </div>
            {i < entries.length - 1 && (
              <span className="text-surface-200/30 text-lg">→</span>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Context cards */}
      {entries.map((entry) => {
        const color = getAgentColor(entry.agent_type);
        return (
          <div
            key={entry.agent_type}
            className="glass-card rounded-lg p-3 border-l-2"
            style={{ borderLeftColor: color }}
          >
            <div className="flex items-center gap-2 mb-2">
              <span>{getAgentIcon(entry.agent_type)}</span>
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color }}>
                {entry.agent_type}
              </span>
              <span className="text-[10px] text-surface-200/30">
                {Object.keys(entry.data).length} entries
              </span>
            </div>
            <div className="space-y-1">
              {Object.entries(entry.data).map(([key, value]) => (
                <div key={key} className="flex items-start gap-2 text-[11px]">
                  <span className="text-surface-200/50 font-mono shrink-0">{key}:</span>
                  <span className="text-surface-200/80 break-all">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
