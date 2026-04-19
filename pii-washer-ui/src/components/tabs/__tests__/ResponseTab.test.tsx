import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ResponseTab } from '../ResponseTab';
import { useSessionStore } from '@/store/session-store';
import * as sessionsApi from '@/api/sessions';
import type { Session, SessionStatusResponse } from '@/types/api';

function makeSession(overrides: Partial<Session> = {}): Session {
  return {
    session_id: 'sess-1',
    status: 'awaiting_response',
    created_at: '2026-04-18T00:00:00Z',
    updated_at: '2026-04-18T00:00:00Z',
    source_format: 'text',
    source_filename: null,
    original_text: 'original',
    pii_detections: [],
    depersonalized_text: '[Person_1]',
    response_text: 'first response [Person_1]',
    repersonalized_text: null,
    unmatched_placeholders: [],
    ...overrides,
  };
}

function makeStatus(): SessionStatusResponse {
  return {
    session_id: 'sess-1',
    status: 'awaiting_response',
    source_format: 'text',
    source_filename: null,
    detection_count: 1,
    confirmed_count: 1,
    rejected_count: 0,
    pending_count: 0,
    has_depersonalized: true,
    has_response: true,
    has_repersonalized: false,
    can_analyze: false,
    can_edit_detections: false,
    can_depersonalize: false,
    can_load_response: false,
    can_repersonalize: true,
  };
}

function renderWithClient() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: 0 } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  const result = render(<ResponseTab />, { wrapper: Wrapper });
  return { client, ...result };
}

describe('ResponseTab state sync', () => {
  beforeEach(() => {
    useSessionStore.setState({
      activeSessionId: 'sess-1',
      activeTab: 'response',
      focusedDetectionId: null,
    });
    vi.restoreAllMocks();
  });

  it('syncs textarea when server response_text changes while status stays awaiting_response', async () => {
    vi.spyOn(sessionsApi, 'getSession').mockImplementation(async () =>
      makeSession({ response_text: 'first response [Person_1]' }),
    );
    vi.spyOn(sessionsApi, 'getSessionStatus').mockResolvedValue(makeStatus());

    const { client } = renderWithClient();

    const textarea = (await screen.findByPlaceholderText(
      /Paste the AI response/i,
    )) as HTMLTextAreaElement;
    expect(textarea.value).toBe('first response [Person_1]');

    // Simulate: a mutation invalidates, refetch happens, new session data lands
    // in the cache. We do this directly with setQueryData — no network roundtrip.
    act(() => {
      client.setQueryData<Session>(
        ['session', 'sess-1'],
        makeSession({ response_text: 'SECOND response [Person_1]' }),
      );
    });

    await waitFor(
      () => {
        expect(
          (screen.getByPlaceholderText(/Paste the AI response/i) as HTMLTextAreaElement).value,
        ).toBe('SECOND response [Person_1]');
      },
      { timeout: 2000 },
    );
  });
});
