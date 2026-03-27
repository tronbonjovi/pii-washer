import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { CheckCheck, Wand2 } from 'lucide-react';
import type { SessionStatusResponse } from '@/types/api';
import { useConfirmAllDetections } from '@/hooks/use-detections';
import { useDepersonalize } from '@/hooks/use-workflow';
import { isAPIError } from '@/types/api';
import { useState } from 'react';
import { toast } from 'sonner';

interface BulkActionsProps {
  sessionId: string;
  sessionStatus: SessionStatusResponse;
}

export function BulkActions({ sessionId, sessionStatus }: BulkActionsProps) {
  const confirmAll = useConfirmAllDetections(sessionId);
  const depersonalize = useDepersonalize(sessionId);
  const [applyError, setApplyError] = useState<string | null>(null);

  function handleApply() {
    setApplyError(null);
    depersonalize.mutate(undefined, {
      onSuccess: () => {
        toast.success('Document depersonalized');
      },
      onError: (err) => {
        let msg: string;
        if (isAPIError(err)) {
          if (err.message.toLowerCase().includes('no confirmed')) {
            msg = 'Confirm at least one detection before applying.';
          } else if (err.code === 'INVALID_STATE') {
            msg = 'This session is not in the right state for depersonalization.';
          } else {
            msg = err.message;
          }
        } else {
          msg = 'Depersonalization failed';
        }
        setApplyError(msg);
        toast.error(msg);
      },
    });
  }

  return (
    <div className="border-t bg-background">
      <Separator />
      <div className="p-3 space-y-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full flex items-center gap-1.5"
          onClick={() => confirmAll.mutate()}
          disabled={sessionStatus.pending_count === 0 || !sessionStatus.can_edit_detections || confirmAll.isPending}
        >
          <CheckCheck className="h-3.5 w-3.5" />
          Confirm All ({sessionStatus.pending_count} pending)
        </Button>
        <Button
          size="sm"
          className="w-full flex items-center gap-1.5"
          onClick={handleApply}
          disabled={!sessionStatus.can_depersonalize || depersonalize.isPending}
        >
          <Wand2 className="h-3.5 w-3.5" />
          {depersonalize.isPending ? 'Applying...' : `Apply (${sessionStatus.confirmed_count}/${sessionStatus.detection_count} confirmed)`}
        </Button>
        {applyError && <p className="text-xs text-destructive">{applyError}</p>}
      </div>
    </div>
  );
}
