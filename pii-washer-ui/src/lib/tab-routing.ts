import type { TabId } from '@/store/session-store';

/**
 * Maps a session's workflow status to the tab where the user should land.
 *
 * The goal: land the user where they left off. A session in 'analyzed' state
 * was last being worked on in the Review tab. A 'repersonalized' session has
 * completed the full pipeline — show the Results.
 *
 * Falls back to 'input' for unknown statuses (defensive — shouldn't happen
 * with valid data, but safe if it does).
 */
export function tabForStatus(status: string | undefined): TabId {
  switch (status) {
    case 'user_input':
      return 'input';
    case 'analyzed':
      return 'review';
    case 'depersonalized':
    case 'awaiting_response':
      return 'response';
    case 'repersonalized':
      return 'results';
    default:
      return 'input';
  }
}
