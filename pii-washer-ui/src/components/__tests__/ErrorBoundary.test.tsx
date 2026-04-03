import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppErrorBoundary } from '../ErrorBoundary';
import { useSessionStore } from '@/store/session-store';

// Suppress React's error boundary console noise during tests
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  useSessionStore.setState({
    activeSessionId: null,
    activeTab: 'input',
    focusedDetectionId: null,
  });
});

// A component that throws on render, controlled by a flag
let shouldThrow = false;
function ThrowingComponent() {
  if (shouldThrow) {
    throw new Error('Test explosion');
  }
  return <p>All good</p>;
}

describe('AppErrorBoundary', () => {
  beforeEach(() => {
    shouldThrow = false;
  });

  it('renders children when no error occurs', () => {
    render(
      <AppErrorBoundary>
        <p>Child content</p>
      </AppErrorBoundary>,
    );

    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('shows error message when a child throws', () => {
    shouldThrow = true;

    render(
      <AppErrorBoundary>
        <ThrowingComponent />
      </AppErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test explosion')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start over/i })).toBeInTheDocument();
  });

  it('Start Over resets the store and re-renders children', async () => {
    const user = userEvent.setup();

    // Put the store in a dirty state
    useSessionStore.setState({
      activeSessionId: 'dirty-session',
      activeTab: 'results',
      focusedDetectionId: 'det-1',
    });

    shouldThrow = true;

    render(
      <AppErrorBoundary>
        <ThrowingComponent />
      </AppErrorBoundary>,
    );

    // Verify we're showing the error UI
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Fix the throw so recovery works
    shouldThrow = false;

    await user.click(screen.getByRole('button', { name: /start over/i }));

    // Children should render again
    expect(screen.getByText('All good')).toBeInTheDocument();

    // Store should be reset
    const state = useSessionStore.getState();
    expect(state.activeSessionId).toBeNull();
    expect(state.activeTab).toBe('input');
    expect(state.focusedDetectionId).toBeNull();
  });
});
