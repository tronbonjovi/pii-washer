import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listSessions,
  createSession,
  uploadFile,
  getSession,
  getSessionStatus,
  deleteSession,
  clearAllSessions,
  exportSession,
  importSession,
} from '@/api/sessions';
import { useSessionStore } from '@/store/session-store';

export function useSessionList() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: listSessions,
  });
}

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

export function useDeleteSession() {
  const queryClient = useQueryClient();
  const { activeSessionId, clearActiveSession } = useSessionStore();

  return useMutation({
    mutationFn: (sessionId: string) => deleteSession(sessionId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.removeQueries({ queryKey: ['session', deletedId] });
      if (activeSessionId === deletedId) {
        clearActiveSession();
      }
    },
  });
}

export function useClearAllSessions() {
  const queryClient = useQueryClient();
  const clearActiveSession = useSessionStore((s) => s.clearActiveSession);

  return useMutation({
    mutationFn: clearAllSessions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      clearActiveSession();
    },
  });
}

export function useExportSession() {
  return useMutation({
    mutationFn: (sessionId: string) => exportSession(sessionId),
  });
}

export function useImportSession() {
  const queryClient = useQueryClient();
  const setActiveSession = useSessionStore((s) => s.setActiveSession);

  return useMutation({
    mutationFn: (sessionData: string) => importSession(sessionData),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setActiveSession(data.session_id);
    },
  });
}
