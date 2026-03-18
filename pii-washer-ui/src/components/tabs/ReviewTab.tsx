import { useEffect } from 'react';
import { useSession, useSessionStatus } from '@/hooks/use-sessions';
import { useSessionStore } from '@/store/session-store';
import { DocumentViewer } from '@/components/review/DocumentViewer';
import { DetectionSidebar } from '@/components/review/DetectionSidebar';
import { DepersonalizedView } from '@/components/review/DepersonalizedView';
import { WorkflowNav } from '@/components/layout/WorkflowNav';
import { Button } from '@/components/ui/button';

export function ReviewTab() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const setActiveTab = useSessionStore((s) => s.setActiveTab);
  const focusedDetectionId = useSessionStore((s) => s.focusedDetectionId);
  const setFocusedDetection = useSessionStore((s) => s.setFocusedDetection);

  const { data: session, isLoading, isError, refetch } = useSession(activeSessionId);
  const { data: sessionStatus } = useSessionStatus(activeSessionId);

  // Clear focus when session changes
  useEffect(() => {
    setFocusedDetection(null);
  }, [activeSessionId, setFocusedDetection]);

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
        <p className="text-sm">Loading session...</p>
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
        <p className="text-sm text-destructive">Failed to load session.</p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  // Post-depersonalization view
  const isDepersonalized =
    session.status === 'depersonalized' ||
    session.status === 'awaiting_response' ||
    session.status === 'repersonalized';

  if (isDepersonalized && session.depersonalized_text) {
    const confirmed = sessionStatus?.confirmed_count ?? session.pii_detections.filter((d) => d.status === 'confirmed').length;
    const rejected = sessionStatus?.rejected_count ?? session.pii_detections.filter((d) => d.status === 'rejected').length;

    return (
      <DepersonalizedView
        depersonalizedText={session.depersonalized_text}
        confirmedCount={confirmed}
        rejectedCount={rejected}
        onContinue={() => setActiveTab('response')}
      />
    );
  }

  // Reviewing state
  function handleDetectionClick(id: string) {
    setFocusedDetection(focusedDetectionId === id ? null : id);
  }

  function handleDocumentClick() {
    setFocusedDetection(null);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Document viewer — 62% width */}
        <div className="flex-[62] min-w-0 h-full overflow-hidden">
          <DocumentViewer
            originalText={session.original_text}
            detections={session.pii_detections}
            focusedDetectionId={focusedDetectionId}
            onDetectionClick={handleDetectionClick}
            onDocumentClick={handleDocumentClick}
          />
        </div>

        {/* Detection sidebar — 38% width */}
        <div className="flex-[38] min-w-0 h-full overflow-hidden">
          {sessionStatus ? (
            <DetectionSidebar
              sessionId={session.session_id}
              detections={session.pii_detections}
              sessionStatus={sessionStatus}
              focusedDetectionId={focusedDetectionId}
              onDetectionClick={handleDetectionClick}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              Loading...
            </div>
          )}
        </div>
      </div>

      <WorkflowNav
        back={{ label: 'Input', tab: 'input' }}
        next={{ label: 'Response', tab: 'response', disabled: true }}
      />
    </div>
  );
}
