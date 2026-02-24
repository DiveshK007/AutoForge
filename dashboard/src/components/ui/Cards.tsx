'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  glowColor?: string;
}

export function GlassCard({
  children,
  className,
  title,
  subtitle,
  icon,
  glowColor,
}: GlassCardProps) {
  return (
    <div
      className={cn(
        'glass-card rounded-xl p-5 transition-all duration-300',
        'hover:border-brand-400/30 hover:shadow-lg hover:shadow-brand-500/5',
        className
      )}
      style={glowColor ? { borderColor: `${glowColor}33` } : undefined}
    >
      {(title || icon) && (
        <div className="flex items-center gap-3 mb-4">
          {icon && <span className="text-xl">{icon}</span>}
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-surface-200 uppercase tracking-wider">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-surface-200/50 mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
      )}
      {children}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  icon?: React.ReactNode;
  color?: string;
}

export function MetricCard({
  label,
  value,
  suffix,
  trend,
  trendValue,
  icon,
  color = '#6366f1',
}: MetricCardProps) {
  const trendIcon = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→';
  const trendColor =
    trend === 'up'
      ? 'text-emerald-400'
      : trend === 'down'
      ? 'text-red-400'
      : 'text-surface-200/50';

  return (
    <div className="glass-card rounded-xl p-4 transition-all duration-300 hover:scale-[1.02]">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-surface-200/60 uppercase tracking-wider">
          {label}
        </span>
        {icon && <span className="text-lg opacity-60">{icon}</span>}
      </div>
      <div className="flex items-end gap-1.5">
        <span
          className="text-2xl font-bold metric-value"
          style={{ color }}
        >
          {value}
        </span>
        {suffix && (
          <span className="text-sm text-surface-200/40 mb-0.5">{suffix}</span>
        )}
      </div>
      {trendValue && (
        <div className={cn('text-xs mt-1.5 flex items-center gap-1', trendColor)}>
          <span>{trendIcon}</span>
          <span>{trendValue}</span>
        </div>
      )}
    </div>
  );
}

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const colorMap: Record<string, string> = {
    completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    running: 'bg-brand-500/20 text-brand-400 border-brand-500/30',
    pending: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    idle: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
    active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  };

  const colors = colorMap[status.toLowerCase()] || colorMap.idle;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium',
        colors,
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs'
      )}
    >
      <span
        className={cn(
          'rounded-full mr-1.5',
          size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2',
          status.toLowerCase() === 'running' && 'animate-pulse'
        )}
        style={{
          backgroundColor: 'currentColor',
        }}
      />
      {status}
    </span>
  );
}
