import { useSessionStore, type TabId } from '@/store/session-store';
import { SessionPanel } from '@/components/session/SessionPanel';
import { ThemeToggle } from './ThemeToggle';
import { useTheme } from '@/components/theme-provider';
import logoDarkSrc from '@/assets/logo-darkmode.png';
import logoLightSrc from '@/assets/logo-lightmode.png';

const STEPS: { id: TabId; label: string; step: number }[] = [
  { id: 'input', label: 'Input', step: 1 },
  { id: 'review', label: 'Review', step: 2 },
  { id: 'response', label: 'Response', step: 3 },
  { id: 'results', label: 'Results', step: 4 },
];

export function Header() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const { activeTab, setActiveTab } = useSessionStore();
  const { resolvedTheme } = useTheme();
  const logoSrc = resolvedTheme === 'dark' ? logoDarkSrc : logoLightSrc;

  return (
    <header className="flex h-20 items-center justify-between px-6">
      {/* Left: Brand */}
      <div className="flex items-center">
        <img src={logoSrc} alt="Pii Washer" className="h-[60px]" />
      </div>

      {/* Center: Navigation */}
      <nav className="flex items-center gap-2">
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
      </nav>

      {/* Right: Theme toggle + Sessions + session ID */}
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <div className="flex flex-col items-end gap-0.5">
          <SessionPanel />
          {activeSessionId && (
            <span className="text-[10px] text-muted-foreground leading-none">
              {activeSessionId}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
