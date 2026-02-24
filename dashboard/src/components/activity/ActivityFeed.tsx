'use client';

import React from 'react';
import { cn, formatTimestamp, getAgentIcon, getStatusColor } from '@/lib/utils';
import { StatusBadge } from '@/components/ui/Cards';
import type { ActivityEvent } from '@/lib/api';

interface ActivityFeedProps {
  events: ActivityEvent[];
  maxItems?: number;
}

export function ActivityFeed({ events, maxItems = 20 }: ActivityFeedProps) {
  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8 text-surface-200/40">
        <p className="text-3xl mb-2">📋</p>
        <p className="text-sm">No activity yet</p>
      </div>
    );
  }

  const displayed = events.slice(0, maxItems);

  return (
    <div className="space-y-1">
      {displayed.map((event, i) => (
        <div
          key={`${event.timestamp}-${i}`}
          className={cn(
            'flex items-start gap-3 px-3 py-2.5 rounded-lg',
            'transition-all duration-200',
            'hover:bg-surface-800/50',
            i === 0 && 'animate-slide-up'
          )}
        >
          {/* Timeline dot */}
          <div className="flex flex-col items-center mt-1.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: getStatusColor(event.status) }}
            />
            {i < displayed.length - 1 && (
              <div className="w-px h-full bg-surface-700 mt-1" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              {event.agent && (
                <span className="text-sm">{getAgentIcon(event.agent)}</span>
              )}
              <span className="text-xs font-medium text-white/80 truncate">
                {event.description}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-surface-200/40">
              <span>{formatTimestamp(event.timestamp)}</span>
              {event.agent && (
                <>
                  <span>•</span>
                  <span className="uppercase">{event.agent}</span>
                </>
              )}
              <StatusBadge status={event.status} size="sm" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
