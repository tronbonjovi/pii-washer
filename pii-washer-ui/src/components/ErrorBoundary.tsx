import { ErrorBoundary as ReactErrorBoundary, type FallbackProps } from 'react-error-boundary';
import { useSessionStore } from '@/store/session-store';
import type { ReactNode } from 'react';

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const resetSession = useSessionStore((s) => s.resetSession);

  const handleStartOver = () => {
    resetSession();
    resetErrorBoundary();
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md space-y-4 text-center">
        <h1 className="text-2xl font-semibold text-foreground">Something went wrong</h1>
        <p className="text-muted-foreground">
          An unexpected error occurred. Your data stays on this machine — nothing was sent anywhere.
        </p>
        <pre className="mt-2 max-h-32 overflow-auto rounded-md bg-muted p-3 text-left text-xs text-muted-foreground">
          {error instanceof Error ? error.message : String(error)}
        </pre>
        <button
          onClick={handleStartOver}
          className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          Start Over
        </button>
      </div>
    </div>
  );
}

export function AppErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ReactErrorBoundary FallbackComponent={ErrorFallback}>
      {children}
    </ReactErrorBoundary>
  );
}
