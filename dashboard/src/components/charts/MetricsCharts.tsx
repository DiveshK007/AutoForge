'use client';

import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { MetricHistory, LearningCurve } from '@/lib/api';

const chartTheme = {
  backgroundColor: 'transparent',
  textColor: '#94a3b8',
  gridColor: '#1e293b',
  tooltipBg: 'rgba(15, 23, 42, 0.95)',
  tooltipBorder: '#334155',
};

interface MetricsChartProps {
  data: MetricHistory[];
}

export function MetricsOverTimeChart({ data }: MetricsChartProps) {
  if (!data || data.length === 0) {
    return <ChartPlaceholder text="Metrics will appear as workflows complete" />;
  }

  const formatted = data.map((d) => ({
    ...d,
    success_rate: d.success_rate * 100,
    confidence: d.confidence * 100,
    time: new Date(d.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={formatted}>
        <defs>
          <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.gridColor} />
        <XAxis
          dataKey="time"
          tick={{ fill: chartTheme.textColor, fontSize: 11 }}
          axisLine={{ stroke: chartTheme.gridColor }}
        />
        <YAxis
          tick={{ fill: chartTheme.textColor, fontSize: 11 }}
          axisLine={{ stroke: chartTheme.gridColor }}
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: chartTheme.tooltipBg,
            border: `1px solid ${chartTheme.tooltipBorder}`,
            borderRadius: '8px',
            color: '#e2e8f0',
            fontSize: '12px',
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: '11px', color: chartTheme.textColor }}
        />
        <Area
          type="monotone"
          dataKey="success_rate"
          name="Success Rate"
          stroke="#10b981"
          fill="url(#colorSuccess)"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="confidence"
          name="Confidence"
          stroke="#6366f1"
          fill="url(#colorConfidence)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

interface LearningChartProps {
  data: LearningCurve[];
}

export function LearningCurveChart({ data }: LearningChartProps) {
  if (!data || data.length === 0) {
    return <ChartPlaceholder text="Learning curve will emerge over time" />;
  }

  const formatted = data.map((d) => ({
    ...d,
    cumulative_success_rate: d.cumulative_success_rate * 100,
    confidence: d.confidence * 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.gridColor} />
        <XAxis
          dataKey="event_number"
          tick={{ fill: chartTheme.textColor, fontSize: 11 }}
          axisLine={{ stroke: chartTheme.gridColor }}
          label={{
            value: 'Events Processed',
            position: 'insideBottom',
            offset: -5,
            fill: chartTheme.textColor,
            fontSize: 11,
          }}
        />
        <YAxis
          tick={{ fill: chartTheme.textColor, fontSize: 11 }}
          axisLine={{ stroke: chartTheme.gridColor }}
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: chartTheme.tooltipBg,
            border: `1px solid ${chartTheme.tooltipBorder}`,
            borderRadius: '8px',
            color: '#e2e8f0',
            fontSize: '12px',
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: '11px', color: chartTheme.textColor }}
        />
        <Line
          type="monotone"
          dataKey="cumulative_success_rate"
          name="Cumulative Success"
          stroke="#10b981"
          strokeWidth={2}
          dot={{ r: 3, fill: '#10b981' }}
        />
        <Line
          type="monotone"
          dataKey="confidence"
          name="Confidence"
          stroke="#6366f1"
          strokeWidth={2}
          dot={{ r: 3, fill: '#6366f1' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

interface CarbonChartProps {
  data: MetricHistory[];
}

export function CarbonSavingsChart({ data }: CarbonChartProps) {
  if (!data || data.length === 0) {
    return <ChartPlaceholder text="Carbon savings data will appear here" />;
  }

  const formatted = data.map((d) => ({
    time: new Date(d.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    carbon_saved: d.carbon_saved,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={formatted}>
        <defs>
          <linearGradient id="colorCarbon" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0.2} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.gridColor} />
        <XAxis
          dataKey="time"
          tick={{ fill: chartTheme.textColor, fontSize: 11 }}
          axisLine={{ stroke: chartTheme.gridColor }}
        />
        <YAxis
          tick={{ fill: chartTheme.textColor, fontSize: 11 }}
          axisLine={{ stroke: chartTheme.gridColor }}
          tickFormatter={(v) => `${v}g`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: chartTheme.tooltipBg,
            border: `1px solid ${chartTheme.tooltipBorder}`,
            borderRadius: '8px',
            color: '#e2e8f0',
            fontSize: '12px',
          }}
          formatter={(value: number) => [`${value.toFixed(2)}g CO₂`, 'Saved']}
        />
        <Bar
          dataKey="carbon_saved"
          name="CO₂ Saved (g)"
          fill="url(#colorCarbon)"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ChartPlaceholder({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center h-[250px] text-surface-200/30">
      <div className="text-center">
        <p className="text-3xl mb-2">📊</p>
        <p className="text-sm">{text}</p>
      </div>
    </div>
  );
}
