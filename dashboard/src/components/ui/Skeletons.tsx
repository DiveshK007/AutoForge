'use client';

import React from 'react';
import { cn } from '@/lib/utils';

/**
 * Animated skeleton placeholder for loading states.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-lg bg-surface-700/40',
        className
      )}
      role="status"
      aria-label="Loading"
    />
  );
}

/**
 * Metric card skeleton — matches MetricCard layout.
 */
export function MetricCardSkeleton() {
  return (
    <div className="glass-card rounded-xl p-4" role="status" aria-label="Loading metric">
      <div className="flex items-center justify-between mb-2">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-5 w-5 rounded-full" />
      </div>
      <Skeleton className="h-8 w-24 mt-1" />
      <Skeleton className="h-3 w-16 mt-2" />
    </div>
  );
}

/**
 * Full metrics row skeleton — 6 cards.
 */
export function MetricsRowSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <MetricCardSkeleton key={i} />
      ))}
    </div>
  );
}

/**
 * Glass card skeleton with title area and content.
 */
export function GlassCardSkeleton({
  height = 'h-[300px]',
  showTitle = true,
}: {
  height?: string;
  showTitle?: boolean;
}) {
  return (
    <div className="glass-card rounded-xl p-5" role="status" aria-label="Loading content">
      {showTitle && (
        <div className="flex items-center gap-3 mb-4">
          <Skeleton className="h-6 w-6 rounded-full" />
          <div className="space-y-1.5">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-48" />
          </div>
        </div>
      )}
      <Skeleton className={cn('w-full rounded-lg', height)} />
    </div>
  );
}

/**
 * Agent grid skeleton — 6 agent cards.
 */
export function AgentGridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="glass-card rounded-xl p-4" role="status" aria-label="Loading agent">
          <div className="flex items-center gap-3 mb-3">
            <Skeleton className="h-10 w-10 rounded-full" />
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-2 w-full rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Activity feed skeleton.
 */
export function ActivityFeedSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading activity">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-start gap-3 p-2">
          <Skeleton className="h-6 w-6 rounded-full flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-2 w-1/2" />
          </div>
          <Skeleton className="h-3 w-14 flex-shrink-0" />
        </div>
      ))}
    </div>
  );
}

/**
 * Full overview tab skeleton.
 */
export function OverviewTabSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading overview">
      <MetricsRowSkeleton />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <GlassCardSkeleton height="h-[280px]" />
          <GlassCardSkeleton height="h-[120px]" />
        </div>
        <div className="space-y-6">
          <GlassCardSkeleton height="h-[180px]" />
          <GlassCardSkeleton height="h-[300px]" />
        </div>
      </div>
    </div>
  );
}
