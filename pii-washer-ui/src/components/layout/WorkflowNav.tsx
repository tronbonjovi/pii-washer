import { Button } from '@/components/ui/button';
import { ArrowLeft, ArrowRight, RotateCcw } from 'lucide-react';
import { useSessionStore, type TabId } from '@/store/session-store';

interface WorkflowNavProps {
  back?: { label: string; tab: TabId };
  next?: { label: string; tab: TabId; disabled?: boolean };
  startNew?: boolean;
}

export function WorkflowNav({ back, next, startNew }: WorkflowNavProps) {
  const { setActiveTab } = useSessionStore();
  const clearActiveSession = useSessionStore((s) => s.clearActiveSession);

  return (
    <div className="flex items-center justify-between border-t pt-3 mt-auto">
      <div>
        {back && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setActiveTab(back.tab)}
            className="flex items-center gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {back.label}
          </Button>
        )}
      </div>
      <div className="flex items-center gap-2">
        {startNew && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              clearActiveSession();
              setActiveTab('input');
            }}
            className="flex items-center gap-1.5"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Start New
          </Button>
        )}
        {next && (
          <Button
            size="sm"
            onClick={() => setActiveTab(next.tab)}
            disabled={next.disabled}
            className="flex items-center gap-1.5"
          >
            {next.label}
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
