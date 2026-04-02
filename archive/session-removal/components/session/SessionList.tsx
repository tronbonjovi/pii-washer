import { useSessionList } from '@/hooks/use-sessions';
import { useSessionStore } from '@/store/session-store';
import { SessionRow } from './SessionRow';

interface SessionListProps {
  onSessionSelect: () => void;
}

export function SessionList({ onSessionSelect }: SessionListProps) {
  const { data: sessions, isLoading, error } = useSessionList();
  const activeSessionId = useSessionStore((s) => s.activeSessionId);

  if (isLoading) {
    return (
      <div className="px-4 py-8 text-center text-sm text-muted-foreground">
        Loading sessions…
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-8 text-center text-sm text-destructive">
        Could not load sessions. Is the backend running?
      </div>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-muted-foreground">
        No sessions yet. Paste or upload a document to get started.
      </div>
    );
  }

  const sorted = [...sessions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="flex flex-col">
      {sorted.map((session) => (
        <SessionRow
          key={session.session_id}
          session={session}
          isActive={session.session_id === activeSessionId}
          onSelect={onSessionSelect}
        />
      ))}
    </div>
  );
}
