import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createSession,
  uploadFile,
  getSession,
  getSessionStatus,
  resetSession,
} from '@/api/sessions';
import { useSessionStore } from '@/store/session-store';

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getSession(sessionId!),
    enabled: !!sessionId,
  });
}

export function useSessionStatus(sessionId: string | null) {
  return useQuery({
    queryKey: ['sessionStatus', sessionId],
    queryFn: () => getSessionStatus(sessionId!),
    enabled: !!sessionId,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  const setActiveSession = useSessionStore((s) => s.setActiveSession);

  return useMutation({
    mutationFn: (text: string) => createSession(text),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setActiveSession(data.session_id);
    },
  });
}

export function useUploadFile() {
  const queryClient = useQueryClient();
  const setActiveSession = useSessionStore((s) => s.setActiveSession);

  return useMutation({
    mutationFn: (file: File) => uploadFile(file),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setActiveSession(data.session_id);
    },
  });
}

export function useResetSession() {
  const queryClient = useQueryClient();
  const resetStore = useSessionStore((s) => s.resetSession);

  return useMutation({
    mutationFn: resetSession,
    onSuccess: () => {
      // Targeted invalidation — only session-scoped queries. Preserves
      // unrelated caches (health, settings, updates).
      queryClient.invalidateQueries({ queryKey: ['session'] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus'] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      resetStore();
    },
  });
}
