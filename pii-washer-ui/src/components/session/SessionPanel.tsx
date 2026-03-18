import { useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { SessionList } from './SessionList';
import { ImportDialog } from './ImportDialog';
import { ClearAllConfirmDialog } from './ClearAllConfirmDialog';
import { useSessionList } from '@/hooks/use-sessions';
import { useSessionStore } from '@/store/session-store';

export function SessionPanel() {
  const [open, setOpen] = useState(false);
  const { data: sessions } = useSessionList();
  const { clearActiveSession, setActiveTab } = useSessionStore();

  function handleNewSession() {
    clearActiveSession();
    setActiveTab('input');
    setOpen(false);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm">
          Sessions
          {sessions && sessions.length > 0 && (
            <span className="ml-1.5 text-xs text-muted-foreground">
              ({sessions.length})
            </span>
          )}
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="flex w-80 flex-col gap-0 p-0 sm:w-96">
        <SheetHeader className="border-b px-4 py-3">
          <SheetTitle>Sessions</SheetTitle>
        </SheetHeader>

        <div className="flex items-center gap-2 border-b px-4 py-2">
          <Button variant="default" size="sm" onClick={handleNewSession}>
            New
          </Button>
          <ImportDialog onSuccess={() => setOpen(false)} />
          {sessions && sessions.length > 0 && (
            <ClearAllConfirmDialog />
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          <SessionList onSessionSelect={() => setOpen(false)} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
