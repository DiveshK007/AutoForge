'use client';

import React from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

interface MISBreakdownProps {
  accuracy: number;
  learning: number;
  reflection: number;
  collaboration: number;
  sustainability: number;
  overall: number;
}

const factorWeights = {
  accuracy: 0.30,
  learning: 0.25,
  reflection: 0.20,
  collaboration: 0.15,
  sustainability: 0.10,
};

export function MISBreakdown({
  accuracy,
  learning,
  reflection,
  collaboration,
  sustainability,
  overall,
}: MISBreakdownProps) {
  const radarData = [
    { factor: 'Accuracy (30%)', value: accuracy, fullMark: 1 },
    { factor: 'Learning (25%)', value: learning, fullMark: 1 },
    { factor: 'Reflection (20%)', value: reflection, fullMark: 1 },
    { factor: 'Collaboration (15%)', value: collaboration, fullMark: 1 },
    { factor: 'Sustainability (10%)', value: sustainability, fullMark: 1 },
  ];

  return (
    <div className="space-y-4">
      {/* Overall MIS Score */}
      <div className="text-center">
        <div className="text-4xl font-bold bg-gradient-to-r from-brand-400 to-brand-600 bg-clip-text text-transparent">
          {(overall * 100).toFixed(1)}
        </div>
        <div className="text-xs text-surface-200/50 uppercase tracking-wider mt-1">
          Meta-Intelligence Score
        </div>
      </div>

      {/* Radar Chart */}
      <div className="w-full h-[250px]">
        <ResponsiveContainer>
          <RadarChart data={radarData}>
            <PolarGrid stroke="rgba(255,255,255,0.08)" />
            <PolarAngleAxis
              dataKey="factor"
              tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 9 }}
            />
            <PolarRadiusAxis
              domain={[0, 1]}
              tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 8 }}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <Radar
              name="MIS"
              dataKey="value"
              stroke="#6366f1"
              fill="#6366f1"
              fillOpacity={0.3}
              strokeWidth={2}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                fontSize: 11,
              }}
              formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Factor Breakdown Bars */}
      <div className="space-y-2">
        {radarData.map((item) => (
          <div key={item.factor} className="flex items-center gap-3">
            <span className="text-[10px] text-surface-200/50 w-32 shrink-0 text-right">
              {item.factor}
            </span>
            <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-400 transition-all duration-700"
                style={{ width: `${item.value * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-surface-200/70 w-10">
              {(item.value * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
