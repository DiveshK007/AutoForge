'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api';

const SCENARIOS = [
  {
    name: 'pipeline_failure_missing_dep',
    label: '💥 Pipeline Failure (Missing Dep)',
    description: 'numpy removed from requirements.txt → 3 test failures',
  },
  {
    name: 'security_vulnerability',
    label: '🛡️ Security Vulnerability',
    description: 'CVE-2024-12345 in cryptography package (CVSS 8.1)',
  },
  {
    name: 'merge_request_opened',
    label: '📝 Merge Request Opened',
    description: 'New feature MR needing code review + test suggestions',
  },
  {
    name: 'inefficient_pipeline',
    label: '🌱 Inefficient Pipeline',
    description: 'Successful but slow pipeline for GreenOps optimization',
  },
];

export function DemoTrigger() {
  const [triggering, setTriggering] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ scenario: string; success: boolean } | null>(null);

  const handleTrigger = async (scenarioName: string) => {
    setTriggering(scenarioName);
    setLastResult(null);
    try {
      const result = await api.triggerTest(scenarioName);
      setLastResult({ scenario: scenarioName, success: true });
    } catch (err) {
      setLastResult({ scenario: scenarioName, success: false });
    } finally {
      setTriggering(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">🎮</span>
        <h3 className="text-sm font-semibold text-surface-200 uppercase tracking-wider">
          Demo Scenarios
        </h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {SCENARIOS.map((s) => (
          <button
            key={s.name}
            onClick={() => handleTrigger(s.name)}
            disabled={triggering !== null}
            className={`
              glass-card rounded-lg p-3 text-left transition-all duration-200
              hover:scale-[1.02] hover:border-brand-400/40
              disabled:opacity-50 disabled:cursor-not-allowed
              ${triggering === s.name ? 'animate-pulse border-brand-400/50' : ''}
            `}
          >
            <p className="text-sm font-medium text-white/90 mb-1">{s.label}</p>
            <p className="text-[10px] text-surface-200/50 leading-relaxed">
              {s.description}
            </p>
          </button>
        ))}
      </div>

      {lastResult && (
        <div
          className={`text-xs px-3 py-2 rounded-lg text-center ${
            lastResult.success
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              : 'bg-red-500/10 text-red-400 border border-red-500/20'
          }`}
        >
          {lastResult.success
            ? `✅ Scenario "${lastResult.scenario}" triggered successfully`
            : `❌ Failed to trigger scenario "${lastResult.scenario}"`}
        </div>
      )}
    </div>
  );
}
