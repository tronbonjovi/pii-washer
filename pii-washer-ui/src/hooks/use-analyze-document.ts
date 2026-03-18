import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createSession, uploadFile } from '@/api/sessions';
import { analyzeSession } from '@/api/workflow';
import { useSessionStore } from '@/store/session-store';

type AnalyzeDocumentInput =
  | { mode: 'existing'; sessionId: string }
  | { mode: 'text'; text: string }
  | { mode: 'file'; file: File };

export function useAnalyzeDocument() {
  const queryClient = useQueryClient();
  const setActiveSession = useSessionStore((s) => s.setActiveSession);
  const setActiveTab = useSessionStore((s) => s.setActiveTab);

  return useMutation({
    mutationFn: async (input: AnalyzeDocumentInput) => {
      let sessionId: string;
      if (input.mode === 'existing') {
        sessionId = input.sessionId;
      } else {
        // Step 1: Create session
        const session =
          input.mode === 'text'
            ? await createSession(input.text)
            : await uploadFile(input.file);
        sessionId = session.session_id;
      }

      // Step 2: Analyze the new session
      const analysis = await analyzeSession(sessionId);

      return {
        sessionId,
        detectionCount: analysis.detection_count,
      };
    },
    onSuccess: (data) => {
      setActiveSession(data.sessionId);
      setActiveTab('review');

      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['session', data.sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus', data.sessionId] });
    },
  });
}
