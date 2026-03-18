import { useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { DeleteConfirmDialog } from './DeleteConfirmDialog';
import { useExportSession } from '@/hooks/use-sessions';
import { isAPIError, type SessionListItem } from '@/types/api';
import { toast } from 'sonner';

interface SessionActionsProps {
  session: SessionListItem;
}

export function SessionActions({ session }: SessionActionsProps) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const exportSession = useExportSession();

  function handleExport() {
    setExportError(null);
    exportSession.mutate(session.session_id, {
      onSuccess: (jsonString) => {
        try {
          triggerDownload(jsonString, session);
          toast.success('Session exported');
        } catch (error) {
          console.error('Failed to start session export download.', error);
          setExportError('Failed to start the export download.');
          toast.error('Failed to start the export download.');
        }
      },
      onError: (error) => {
        console.error('Failed to export session.', error);
        const msg = isAPIError(error) ? error.message : 'Failed to export session.';
        setExportError(msg);
        toast.error(msg);
      },
    });
  }

  return (
    <>
      <div className="flex flex-col items-end gap-1">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              aria-label="Session actions"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="currentColor"
                stroke="none"
              >
                <circle cx="12" cy="5" r="2" />
                <circle cx="12" cy="12" r="2" />
                <circle cx="12" cy="19" r="2" />
              </svg>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={handleExport}
              disabled={exportSession.isPending}
            >
              {exportSession.isPending ? 'Exporting…' : 'Export'}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => setDeleteOpen(true)}
              className="text-destructive focus:text-destructive"
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        {exportError && (
          <p className="max-w-40 text-right text-xs text-destructive" role="alert">
            {exportError}
          </p>
        )}
      </div>

      <DeleteConfirmDialog
        session={session}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
      />
    </>
  );
}

/**
 * Creates a temporary download link and programmatically clicks it
 * to trigger a browser file-save dialog.
 */
function triggerDownload(jsonString: string, session: SessionListItem) {
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;

  const baseName = session.source_filename
    ? session.source_filename.replace(/\.[^.]+$/, '')
    : session.session_id;
  anchor.download = `pii-washer-${baseName}.json`;

  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
