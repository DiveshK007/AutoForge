'use client';

import React from 'react';

interface MetaScoreProps {
  score: number; // 0-100
}

export function MetaIntelligenceScore({ score }: MetaScoreProps) {
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const color =
    score >= 80 ? '#10b981' : score >= 60 ? '#6366f1' : score >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="rgba(30, 41, 59, 0.8)"
            strokeWidth="6"
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-1000 ease-out"
            style={{
              filter: `drop-shadow(0 0 6px ${color}66)`,
            }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold metric-value" style={{ color }}>
            {score.toFixed(0)}
          </span>
          <span className="text-[10px] text-surface-200/50 uppercase tracking-wider">
            MIS
          </span>
        </div>
      </div>
      <p className="text-xs text-surface-200/50 mt-2 text-center">
        Meta Intelligence Score
      </p>
      <p className="text-[10px] text-surface-200/30 mt-0.5">
        (Accuracy + Learning + Reflection + Collaboration) / 4
      </p>
    </div>
  );
}
