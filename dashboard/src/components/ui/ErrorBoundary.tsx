'use client';

import React, { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * Enterprise-grade Error Boundary.
 * Catches rendering errors in child components and displays a recovery UI.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[AutoForge ErrorBoundary]', error, errorInfo);
    this.props.onError?.(error, errorInfo);
    this.setState({ errorInfo });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center" role="alert">
          <div className="text-3xl mb-3">⚠️</div>
          <h3 className="text-sm font-semibold text-red-400 mb-2">
            Something went wrong
          </h3>
          <p className="text-xs text-surface-200/50 mb-4 max-w-md mx-auto">
            {this.state.error?.message || 'An unexpected error occurred in this component.'}
          </p>
          <button
            onClick={this.handleRetry}
            className="px-4 py-2 text-xs font-medium rounded-lg bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30 transition-all"
          >
            Retry
          </button>
          {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
            <details className="mt-4 text-left text-[10px] text-surface-200/30 max-h-32 overflow-auto">
              <summary className="cursor-pointer mb-1">Stack trace</summary>
              <pre className="whitespace-pre-wrap break-words">
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Functional wrapper for convenient use in JSX.
 */
export function SafeComponent({
  children,
  fallbackMessage,
}: {
  children: ReactNode;
  fallbackMessage?: string;
}) {
  return (
    <ErrorBoundary
      fallback={
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-center">
          <span className="text-xs text-amber-400">
            {fallbackMessage || 'This section could not be loaded.'}
          </span>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
