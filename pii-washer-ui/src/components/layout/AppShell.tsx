import { Header } from './Header';
import { InputTab } from '@/components/tabs/InputTab';
import { ReviewTab } from '@/components/tabs/ReviewTab';
import { ResponseTab } from '@/components/tabs/ResponseTab';
import { ResultsTab } from '@/components/tabs/ResultsTab';
import { useSessionStore } from '@/store/session-store';

const TAB_COMPONENTS = {
  input: InputTab,
  review: ReviewTab,
  response: ResponseTab,
  results: ResultsTab,
} as const;

export function AppShell() {
  const activeTab = useSessionStore((s) => s.activeTab);
  const ActiveTabComponent = TAB_COMPONENTS[activeTab];

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <div className="bg-card border-b shadow-sm">
        <Header />
      </div>
      <main className="flex-1 overflow-auto p-6">
        <ActiveTabComponent />
      </main>
    </div>
  );
}
