'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface LearningDataPoint {
  timestamp: string;
  agent_type: string;
  confidence: number;
  cumulative_success_rate: number;
  experience_count: number;
}

interface LearningCurveChartProps {
  data: LearningDataPoint[];
}

const agentColors: Record<string, string> = {
  sre: '#3b82f6',
  security: '#ef4444',
  qa: '#22c55e',
  review: '#f59e0b',
  docs: '#8b5cf6',
  greenops: '#10b981',
};

export function LearningCurveChart({ data }: LearningCurveChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-surface-200/40">
        <p className="text-sm">No learning data — agents will learn as they process events</p>
      </div>
    );
  }

  // Group by agent and transform for chart
  const agents = Array.from(new Set(data.map(d => d.agent_type)));

  // Create time-series with all agents
  const timePoints = Array.from(new Set(data.map(d => d.timestamp))).sort();
  const chartData = timePoints.map(ts => {
    const point: Record<string, number | string> = { timestamp: ts };
    agents.forEach(agent => {
      const dp = data.find(d => d.timestamp === ts && d.agent_type === agent);
      if (dp) {
        point[`${agent}_confidence`] = dp.confidence;
        point[`${agent}_success`] = dp.cumulative_success_rate;
      }
    });
    return point;
  });

  return (
    <div className="w-full h-[300px]">
      <ResponsiveContainer>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="timestamp"
            tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
            tickFormatter={(v) => new Date(v).toLocaleTimeString()}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              fontSize: 11,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
          />
          {agents.map(agent => (
            <Line
              key={agent}
              type="monotone"
              dataKey={`${agent}_confidence`}
              name={`${agent.toUpperCase()} confidence`}
              stroke={agentColors[agent] || '#6b7280'}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
