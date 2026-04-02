import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useClearAllSessions, useSessionList } from '@/hooks/use-sessions';
import { isAPIError } from '@/types/api';
import { toast } from 'sonner';

export function ClearAllConfirmDialog() {
  const [open, setOpen] = useState(false);
  const clearAll = useClearAllSessions();
  const { data: sessions } = useSessionList();

  const count = sessions?.length ?? 0;
  const errorMessage = clearAll.error
    ? isAPIError(clearAll.error)
      ? clearAll.error.message
      : 'Failed to delete all sessions.'
    : null;

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      clearAll.reset();
    }
    setOpen(nextOpen);
  }

  function handleClearAll() {
    clearAll.mutate(undefined, {
      onSuccess: () => {
        handleOpenChange(false);
        toast.success('All sessions cleared');
      },
      onError: (err) => {
        toast.error(isAPIError(err) ? err.message : 'Failed to delete all sessions.');
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="text-destructive hover:text-destructive"
        >
          Clear all
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete all sessions?</DialogTitle>
          <DialogDescription>
            This will permanently delete{' '}
            {count === 1
              ? 'the 1 session'
              : `all ${count} sessions`}{' '}
            and all associated data. This cannot be undone.
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
            onClick={handleClearAll}
            disabled={clearAll.isPending}
          >
            {clearAll.isPending ? 'Deleting…' : 'Delete all'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
