'use client';

import React, { useState } from 'react';
import { useAuth } from './AuthProvider';

export function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
    } catch {
      setError('Invalid credentials. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-950">
      <div className="w-full max-w-md p-8 rounded-2xl bg-surface-900/80 border border-surface-700/50 backdrop-blur-lg shadow-2xl">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <span className="text-4xl">⚒️</span>
          <div className="text-center">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-400 to-brand-300 bg-clip-text text-transparent">
              AutoForge
            </h1>
            <p className="text-xs text-surface-200/50">
              Autonomous AI Engineering Orchestrator
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Username */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-surface-200/70 mb-1.5">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-surface-800/60 border border-surface-600/50
                         text-surface-100 placeholder-surface-400/50
                         focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400/50
                         transition-colors"
              placeholder="admin"
            />
          </div>

          {/* Password */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-surface-200/70 mb-1.5">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-surface-800/60 border border-surface-600/50
                         text-surface-100 placeholder-surface-400/50
                         focus:outline-none focus:ring-2 focus:ring-brand-400/50 focus:border-brand-400/50
                         transition-colors"
              placeholder="••••••••"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-2.5 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-lg font-semibold text-sm
                       bg-gradient-to-r from-brand-500 to-brand-400 text-white
                       hover:from-brand-400 hover:to-brand-300
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all shadow-lg shadow-brand-500/20"
          >
            {submitting ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-surface-200/30">
          Default credentials: admin / admin
        </p>
      </div>
    </div>
  );
}
