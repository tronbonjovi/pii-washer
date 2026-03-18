import { ScrollArea } from '@/components/ui/scroll-area';
import type { Detection, SessionStatusResponse } from '@/types/api';
import { DetectionSummary } from './DetectionSummary';
import { DetectionCard } from './DetectionCard';
import { ManualAddForm } from './ManualAddForm';
import { BulkActions } from './BulkActions';

interface DetectionSidebarProps {
  sessionId: string;
  detections: Detection[];
  sessionStatus: SessionStatusResponse;
  focusedDetectionId: string | null;
  onDetectionClick: (id: string) => void;
}

export function DetectionSidebar({
  sessionId,
  detections,
  sessionStatus,
  focusedDetectionId,
  onDetectionClick,
}: DetectionSidebarProps) {
  // Sort detections by first position start
  const sorted = [...detections].sort((a, b) => {
    const aStart = a.positions[0]?.start ?? Infinity;
    const bStart = b.positions[0]?.start ?? Infinity;
    return aStart - bStart;
  });

  return (
    <div className="flex flex-col h-full border-l">
      {/* Pinned summary at top */}
      <DetectionSummary detections={detections} />

      {/* Scrollable detection cards */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-2 space-y-2">
          {sorted.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">No detections yet</p>
          ) : (
            sorted.map((det) => (
              <DetectionCard
                key={det.id}
                detection={det}
                sessionId={sessionId}
                isFocused={focusedDetectionId === det.id}
                onClick={onDetectionClick}
              />
            ))
          )}
        </div>
      </ScrollArea>

      {/* Manual add form — collapsible */}
      <ManualAddForm sessionId={sessionId} />

      {/* Pinned bulk actions at bottom */}
      <BulkActions sessionId={sessionId} sessionStatus={sessionStatus} />
    </div>
  );
}
