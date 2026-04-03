import { Monitor, Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/theme-provider';

const CYCLE: Array<'system' | 'light' | 'dark'> = ['system', 'light', 'dark'];

const ICONS = {
  system: Monitor,
  light: Sun,
  dark: Moon,
} as const;

const LABELS = {
  system: 'System theme',
  light: 'Light mode',
  dark: 'Dark mode',
} as const;

type Theme = (typeof CYCLE)[number];

export function ThemeToggle() {
  const { theme: rawTheme, setTheme } = useTheme();
  const theme = (rawTheme ?? 'system') as Theme;
  const Icon = ICONS[theme];
  const nextIndex = (CYCLE.indexOf(theme) + 1) % CYCLE.length;
  const next = CYCLE[nextIndex]!;

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 w-8 p-0"
      onClick={() => setTheme(next)}
      aria-label={`${LABELS[theme]} — click for ${LABELS[next].toLowerCase()}`}
    >
      <Icon className="h-4 w-4" />
    </Button>
  );
}
