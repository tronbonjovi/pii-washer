import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  depersonalizeSession,
  loadResponseText,
  repersonalizeSession,
} from '@/api/workflow';
import type { Session } from '@/types/api';

export function useDepersonalize(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => depersonalizeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus', sessionId] });
    },
  });
}

export function useLoadResponse(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (text: string) => loadResponseText(sessionId, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus', sessionId] });
    },
  });
}

export function useRepersonalize(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => repersonalizeSession(sessionId),
    onSuccess: (data) => {
      // Immediately update the cached session so ResultsTab renders without a stale-state flash
      queryClient.setQueryData<Session>(['session', sessionId], (old) =>
        old
          ? {
              ...old,
              status: 'repersonalized',
              repersonalized_text: data.repersonalized_text,
              unmatched_placeholders: data.unmatched_placeholders,
            }
          : old
      );
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}
