import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useDeleteSession } from '@/hooks/use-sessions';
import { isAPIError, type SessionListItem } from '@/types/api';
import { toast } from 'sonner';

interface DeleteConfirmDialogProps {
  session: SessionListItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeleteConfirmDialog({
  session,
  open,
  onOpenChange,
}: DeleteConfirmDialogProps) {
  const deleteSession = useDeleteSession();

  const sourceLabel = session.source_filename ?? 'Pasted text';
  const errorMessage = deleteSession.error
    ? isAPIError(deleteSession.error)
      ? deleteSession.error.message
      : 'Failed to delete session.'
    : null;

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      deleteSession.reset();
    }
    onOpenChange(nextOpen);
  }

  function handleDelete() {
    deleteSession.mutate(session.session_id, {
      onSuccess: () => {
        handleOpenChange(false);
        toast.success('Session deleted');
      },
      onError: (err) => {
        toast.error(isAPIError(err) ? err.message : 'Failed to delete session.');
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete session?</DialogTitle>
          <DialogDescription>
            This will permanently delete the session "{sourceLabel}" and all its
            data. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        {errorMessage && (
          <p className="text-sm text-destructive" role="alert">
            {errorMessage}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteSession.isPending}
          >
            {deleteSession.isPending ? 'Deleting…' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
