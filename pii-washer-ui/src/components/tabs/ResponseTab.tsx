import { useState, useEffect, useRef } from 'react';
import { useSession, useSessionStatus } from '@/hooks/use-sessions';
import { useLoadResponse, useRepersonalize } from '@/hooks/use-workflow';
import { useSessionStore } from '@/store/session-store';
import { PlaceholderMap } from '@/components/response/PlaceholderMap';
import { NoSessionAlert } from '@/components/layout/NoSessionAlert';
import { WorkflowNav } from '@/components/layout/WorkflowNav';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { isAPIError } from '@/types/api';
import { Wand2 } from 'lucide-react';
import { toast } from 'sonner';

function responseTextKey(text: string | null | undefined): string {
  if (!text) return 'empty';
  // Fingerprint = length + prefix — enough to detect content changes without
  // storing the full text in a React key.
  return `${text.length}:${text.slice(0, 128)}`;
}

export function ResponseTab() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const setActiveTab = useSessionStore((s) => s.setActiveTab);

  const { data: session, isLoading, isError, refetch } = useSession(activeSessionId);
  const { data: sessionStatus } = useSessionStatus(activeSessionId);

  const [responseText, setResponseText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const sessionSnapshotRef = useRef<string | null>(null);

  const loadResponse = useLoadResponse(activeSessionId ?? '');
  const repersonalize = useRepersonalize(activeSessionId ?? '');

  const isBusy = loadResponse.isPending || repersonalize.isPending;

  const snapshotKey = session
    ? `${session.session_id}:${session.status}:${responseTextKey(session.response_text)}`
    : activeSessionId
      ? `loading:${activeSessionId}`
      : null;

  // Sync responseText when the session changes — legitimate "initialize controlled
  // input from fetched data" pattern; not a cascading-render risk because the ref
  // guard ensures it fires at most once per session snapshot.
  useEffect(() => {
    if (sessionSnapshotRef.current === snapshotKey) return;
    sessionSnapshotRef.current = snapshotKey;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time init from server data, guarded by ref
    setResponseText(
      session?.status === 'awaiting_response' && session.response_text
        ? session.response_text
        : ''
    );
  }, [snapshotKey]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!activeSessionId) {
    return <NoSessionAlert />;
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
        <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
      </div>
    );
  }

  // Guard: session must be depersonalized or later to use this tab
  const canUse =
    session.status === 'depersonalized' ||
    session.status === 'awaiting_response' ||
    session.status === 'repersonalized';

  if (!canUse) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
        <p className="text-sm">Complete the Review tab first.</p>
        <Button variant="outline" size="sm" onClick={() => setActiveTab('review')}>
          Go to Review
        </Button>
      </div>
    );
  }

  // If already repersonalized, redirect to results
  if (session.status === 'repersonalized') {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
        <p className="text-sm">Repersonalization complete.</p>
        <Button size="sm" onClick={() => setActiveTab('results')}>View Results</Button>
      </div>
    );
  }

  function handleRepersonalize() {
    if (!responseText.trim()) return;
    setError(null);

    const doRepersonalize = () => {
      repersonalize.mutate(undefined, {
        onSuccess: () => {
          setActiveTab('results');
          toast.success('Document repersonalized');
        },
        onError: (err) => {
          const msg = isAPIError(err) ? err.message : 'Repersonalization failed';
          setError(msg);
          toast.error(msg);
        },
      });
    };

    if (session?.status === 'awaiting_response') {
      doRepersonalize();
      return;
    }

    loadResponse.mutate(responseText, {
      onSuccess: doRepersonalize,
      onError: (err) => {
        const msg = isAPIError(err) ? err.message : 'Failed to load response text';
        setError(msg);
        toast.error(msg);
      },
    });
  }

  const pendingCount = sessionStatus?.pending_count ?? 0;
  const confirmedCount = sessionStatus?.confirmed_count ?? 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: placeholder reference map — 38% */}
        <div className="flex-[38] min-w-0 h-full overflow-hidden">
          <PlaceholderMap detections={session.pii_detections} />
        </div>

        {/* Right: response input + action — 62% */}
        <div className="flex-[62] min-w-0 h-full flex flex-col p-6 gap-4">
          <div>
            <h2 className="text-lg font-semibold">Paste AI Response</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Copy your depersonalized text to your AI tool, get a response, then paste it here.
              The response should contain the placeholders (e.g. <span className="font-mono">[Person_1]</span>).
            </p>
            {pendingCount > 0 && (
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                {pendingCount} detection{pendingCount !== 1 ? 's' : ''} still pending — only confirmed detections will be restored.
              </p>
            )}
          </div>

          <Textarea
            className="flex-1 min-h-0 font-mono text-sm resize-none"
            placeholder="Paste the AI response here..."
            value={responseText}
            onChange={(e) => setResponseText(e.target.value)}
            disabled={isBusy}
          />

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground">
              {confirmedCount} placeholder{confirmedCount !== 1 ? 's' : ''} will be restored
            </p>
            <Button
              onClick={handleRepersonalize}
              disabled={!responseText.trim() || isBusy}
              className="flex items-center gap-2"
            >
              <Wand2 className="h-4 w-4" />
              {isBusy ? 'Restoring...' : 'Restore Original Values'}
            </Button>
          </div>
        </div>
      </div>

      <WorkflowNav
        back={{ label: 'Review', tab: 'review' }}
        next={{ label: 'Results', tab: 'results', disabled: true }}
      />
    </div>
  );
}
