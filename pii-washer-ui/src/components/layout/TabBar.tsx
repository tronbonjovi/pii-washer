import { useSessionStore, type TabId } from '@/store/session-store';

const STEPS: { id: TabId; label: string; step: number }[] = [
  { id: 'input', label: 'Input', step: 1 },
  { id: 'review', label: 'Review', step: 2 },
  { id: 'response', label: 'Response', step: 3 },
  { id: 'results', label: 'Results', step: 4 },
];

export function TabBar() {
  const { activeTab, setActiveTab } = useSessionStore();

  return (
    <nav className="pb-2">
      <div className="flex items-center justify-center gap-2">
        {STEPS.map((step) => {
          const isActive = activeTab === step.id;
          return (
            <button
              key={step.id}
              onClick={() => setActiveTab(step.id)}
              className={[
                'flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition-colors duration-150',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent',
              ].join(' ')}
            >
              <span
                className={[
                  'flex h-5 w-5 items-center justify-center rounded-full text-xs font-semibold',
                  isActive
                    ? 'bg-primary-foreground text-primary'
                    : 'bg-muted text-muted-foreground',
                ].join(' ')}
              >
                {step.step}
              </span>
              {step.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
