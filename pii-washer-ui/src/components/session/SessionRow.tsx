import type { SessionListItem } from '@/types/api';
import { useSessionStore } from '@/store/session-store';
import { tabForStatus } from '@/lib/tab-routing';
import { SessionActions } from './SessionActions';

interface SessionRowProps {
  session: SessionListItem;
  isActive: boolean;
  onSelect: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  user_input: 'Not analyzed',
  analyzed: 'Analyzed',
  depersonalized: 'Depersonalized',
  awaiting_response: 'Awaiting response',
  repersonalized: 'Complete',
};

export function SessionRow({ session, isActive, onSelect }: SessionRowProps) {
  const { setActiveSession, setActiveTab } = useSessionStore();

  function handleClick() {
    setActiveSession(session.session_id);
    setActiveTab(tabForStatus(session.status));
    onSelect();
  }

  const createdDate = new Date(session.created_at);
  const timeLabel = formatSessionTime(createdDate);

  const sourceLabel = session.source_filename ?? 'Pasted text';

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      className={[
        'flex items-start gap-3 border-b px-4 py-3 text-left transition-colors',
        'hover:bg-accent/50 cursor-pointer',
        isActive ? 'bg-accent' : '',
      ].join(' ')}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="truncate text-sm font-medium">{sourceLabel}</span>
          <span className="shrink-0 text-xs text-muted-foreground">{timeLabel}</span>
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{STATUS_LABELS[session.status] ?? session.status}</span>
          {session.detection_count > 0 && (
            <>
              <span>·</span>
              <span>
                {session.detection_count} detection{session.detection_count !== 1 ? 's' : ''}
              </span>
            </>
          )}
        </div>
      </div>

      <div
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <SessionActions session={session} />
      </div>
    </div>
  );
}

/**
 * Formats a date for display in the session list.
 * - Today: "2:34 PM"
 * - This year: "Mar 14"
 * - Older: "Mar 14, 2025"
 */
function formatSessionTime(date: Date): string {
  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (isToday) {
    return date.toLocaleTimeString(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  const isThisYear = date.getFullYear() === now.getFullYear();
  if (isThisYear) {
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  }

  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
