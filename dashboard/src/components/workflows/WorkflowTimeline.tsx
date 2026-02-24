'use client';

import React from 'react';
import { cn, formatTimestamp, getAgentColor, getAgentIcon } from '@/lib/utils';
import { StatusBadge } from '@/components/ui/Cards';
import type { TimelineEntry } from '@/lib/api';

interface WorkflowTimelineProps {
  entries: TimelineEntry[];
}

export function WorkflowTimeline({ entries }: WorkflowTimelineProps) {
  if (!entries || entries.length === 0) {
    return (
      <div className="text-center py-6 text-surface-200/40">
        <p className="text-sm">No timeline data</p>
      </div>
    );
  }

  return (
    <div className="relative pl-6">
      {/* Vertical line */}
      <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-brand-500/50 via-brand-500/20 to-transparent" />

      <div className="space-y-4">
        {entries.map((entry, i) => {
          const agentColor = entry.agent
            ? getAgentColor(entry.agent)
            : '#6366f1';

          return (
            <div key={`${entry.timestamp}-${i}`} className="relative flex gap-4">
              {/* Node */}
              <div
                className="absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 bg-surface-900"
                style={{ borderColor: agentColor }}
              />

              {/* Content */}
              <div className="flex-1 glass-card rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: agentColor }}>
                      {entry.phase}
                    </span>
                    {entry.agent && (
                      <span className="text-sm">{getAgentIcon(entry.agent)}</span>
                    )}
                  </div>
                  <StatusBadge status={entry.status} size="sm" />
                </div>
                <p className="text-xs text-surface-200/70 leading-relaxed">
                  {entry.description}
                </p>
                <p className="text-[10px] text-surface-200/30 mt-1.5">
                  {formatTimestamp(entry.timestamp)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
