import { useSession, useSessionStatus } from '@/hooks/use-sessions';
import { useSessionStore } from '@/store/session-store';
import { RepersonalizedView } from '@/components/results/RepersonalizedView';
import { WorkflowNav } from '@/components/layout/WorkflowNav';
import { Button } from '@/components/ui/button';

export function ResultsTab() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const setActiveTab = useSessionStore((s) => s.setActiveTab);

  const { data: session, isLoading, isError, refetch } = useSession(activeSessionId);
  const { data: sessionStatus } = useSessionStatus(activeSessionId);

  if (!activeSessionId) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
        <p className="text-lg font-medium">No document loaded</p>
        <p className="text-sm">Go to the Input tab to get started.</p>
        <Button variant="outline" size="sm" className="mt-2" onClick={() => setActiveTab('input')}>
          Go to Input
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground">
        <p className="text-sm">Loading...</p>
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
        <p className="text-sm text-destructive">Failed to load session.</p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
      </div>
    );
  }

  if (session.status !== 'repersonalized' || !session.repersonalized_text) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
        <p className="text-sm">No repersonalized result yet.</p>
        <Button variant="outline" size="sm" onClick={() => setActiveTab('response')}>
          Go to Response
        </Button>
      </div>
    );
  }

  const confirmedCount = sessionStatus?.confirmed_count ?? session.pii_detections.filter((d) => d.status === 'confirmed').length;
  const rejectedCount = sessionStatus?.rejected_count ?? session.pii_detections.filter((d) => d.status === 'rejected').length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 min-h-0 overflow-hidden">
        <RepersonalizedView
          repersonalizedText={session.repersonalized_text}
          unmatchedPlaceholders={session.unmatched_placeholders}
          confirmedCount={confirmedCount}
          rejectedCount={rejectedCount}
        />
      </div>

      <WorkflowNav
        back={{ label: 'Response', tab: 'response' }}
        startNew
      />
    </div>
  );
}
