import { Button } from '@/components/ui/button';
import { useSessionStore } from '@/store/session-store';

export function NoSessionAlert() {
  const setActiveTab = useSessionStore((s) => s.setActiveTab);

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
