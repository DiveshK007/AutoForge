import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${min}m ${sec.toFixed(0)}s`;
}

export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function getAgentColor(agentType: string): string {
  const colors: Record<string, string> = {
    sre: '#6366f1',
    security: '#ef4444',
    qa: '#10b981',
    review: '#f59e0b',
    docs: '#3b82f6',
    greenops: '#22c55e',
  };
  return colors[agentType.toLowerCase()] || '#8b5cf6';
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: '#10b981',
    running: '#6366f1',
    pending: '#f59e0b',
    failed: '#ef4444',
    cancelled: '#6b7280',
  };
  return colors[status.toLowerCase()] || '#6b7280';
}

export function getAgentIcon(agentType: string): string {
  const icons: Record<string, string> = {
    sre: '🔧',
    security: '🛡️',
    qa: '🧪',
    review: '📝',
    docs: '📚',
    greenops: '🌱',
  };
  return icons[agentType.toLowerCase()] || '🤖';
}
