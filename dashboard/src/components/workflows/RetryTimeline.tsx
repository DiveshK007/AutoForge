'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface RetryEvent {
  attempt: number;
  maxAttempts: number;
  agent: string;
  strategy: string;
  outcome: 'success' | 'failure' | 'pending';
  confidence?: number;
  duration_ms?: number;
}

interface RetryTimelineProps {
  retries: RetryEvent[];
  className?: string;
}

/**
 * Retry visualization — shows the self-correction journey of an agent.
 */
export function RetryTimeline({ retries, className }: RetryTimelineProps) {
  if (!retries || retries.length === 0) {
    return (
      <div className="text-xs text-surface-200/40 text-center py-4">
        No retries recorded — first attempt succeeded.
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)} role="list" aria-label="Retry timeline">
      {retries.map((retry, idx) => {
        const isLast = idx === retries.length - 1;
        const statusColor =
          retry.outcome === 'success'
            ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400'
            : retry.outcome === 'failure'
            ? 'border-red-500 bg-red-500/20 text-red-400'
            : 'border-amber-500 bg-amber-500/20 text-amber-400';

        const dotColor =
          retry.outcome === 'success'
            ? 'bg-emerald-500'
            : retry.outcome === 'failure'
            ? 'bg-red-500'
            : 'bg-amber-500';

        return (
          <div key={idx} className="flex gap-3" role="listitem">
            {/* Timeline spine */}
            <div className="flex flex-col items-center">
              <div className={cn('w-3 h-3 rounded-full border-2 flex-shrink-0', statusColor)} />
              {!isLast && <div className="w-px flex-1 bg-surface-700/60 my-1" />}
            </div>

            {/* Content */}
            <div className="flex-1 pb-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-surface-200/80">
                  Attempt {retry.attempt}/{retry.maxAttempts}
                </span>
                <span
                  className={cn(
                    'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border',
                    statusColor
                  )}
                >
                  <span className={cn('w-1.5 h-1.5 rounded-full mr-1', dotColor)} />
                  {retry.outcome}
                </span>
              </div>
              <p className="text-xs text-surface-200/50">
                <span className="text-surface-200/70 font-medium">{retry.agent.toUpperCase()}</span>
                {' — '}
                {retry.strategy}
              </p>
              <div className="flex gap-3 mt-1">
                {retry.confidence !== undefined && (
                  <span className="text-[10px] text-surface-200/40">
                    Confidence: {(retry.confidence * 100).toFixed(0)}%
                  </span>
                )}
                {retry.duration_ms !== undefined && (
                  <span className="text-[10px] text-surface-200/40">
                    Duration: {retry.duration_ms}ms
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Compact retry badge — shows retry count inline.
 */
export function RetryBadge({ count, max }: { count: number; max: number }) {
  if (count === 0) return null;

  const isExhausted = count >= max;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border',
        isExhausted
          ? 'border-red-500/30 bg-red-500/10 text-red-400'
          : 'border-amber-500/30 bg-amber-500/10 text-amber-400'
      )}
      aria-label={`${count} retry attempts out of ${max}`}
    >
      🔄 {count}/{max}
    </span>
  );
}
