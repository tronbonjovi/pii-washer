import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionStore } from '../session-store';

// Reset store state before each test so tests don't leak into each other
beforeEach(() => {
  useSessionStore.setState({
    activeSessionId: null,
    activeTab: 'input',
    focusedDetectionId: null,
  });
});

describe('useSessionStore', () => {
  it('has correct default state', () => {
    const state = useSessionStore.getState();
    expect(state.activeSessionId).toBeNull();
    expect(state.activeTab).toBe('input');
    expect(state.focusedDetectionId).toBeNull();
  });

  it('setActiveSession sets the session ID', () => {
    useSessionStore.getState().setActiveSession('session-123');
    expect(useSessionStore.getState().activeSessionId).toBe('session-123');
  });

  it('setActiveTab changes the active tab', () => {
    useSessionStore.getState().setActiveTab('review');
    expect(useSessionStore.getState().activeTab).toBe('review');

    useSessionStore.getState().setActiveTab('results');
    expect(useSessionStore.getState().activeTab).toBe('results');
  });

  it('setFocusedDetection sets and clears detection focus', () => {
    useSessionStore.getState().setFocusedDetection('det-456');
    expect(useSessionStore.getState().focusedDetectionId).toBe('det-456');

    useSessionStore.getState().setFocusedDetection(null);
    expect(useSessionStore.getState().focusedDetectionId).toBeNull();
  });

  it('resetSession resets all state to defaults', () => {
    // Set everything to non-default values
    useSessionStore.setState({
      activeSessionId: 'session-789',
      activeTab: 'response',
      focusedDetectionId: 'det-abc',
    });

    useSessionStore.getState().resetSession();

    const state = useSessionStore.getState();
    expect(state.activeSessionId).toBeNull();
    expect(state.activeTab).toBe('input');
    expect(state.focusedDetectionId).toBeNull();
  });
});
