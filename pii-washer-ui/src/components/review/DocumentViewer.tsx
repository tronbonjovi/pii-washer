import { ScrollArea } from '@/components/ui/scroll-area';
import { HighlightSpan } from './HighlightSpan';
import type { Detection } from '@/types/api';

interface Segment {
  type: 'plain' | 'highlight';
  text: string;
  detection?: Detection;
  /** True only for the first rendered span of a given detection */
  isFirstOccurrence?: boolean;
}

function buildSegments(text: string, detections: Detection[]): Segment[] {
  const ranges: { start: number; end: number; detection: Detection }[] = [];
  for (const det of detections) {
    for (const pos of det.positions) {
      ranges.push({ start: pos.start, end: pos.end, detection: det });
    }
  }

  // Sort by start; on tie, longer range first
  ranges.sort((a, b) => a.start - b.start || b.end - a.end);

  const segments: Segment[] = [];
  const seenDetections = new Set<string>();
  let cursor = 0;

  for (const range of ranges) {
    // Skip overlapping ranges
    if (range.start < cursor) continue;

    if (range.start > cursor) {
      segments.push({ type: 'plain', text: text.slice(cursor, range.start) });
    }

    const isFirstOccurrence = !seenDetections.has(range.detection.id);
    seenDetections.add(range.detection.id);

    segments.push({
      type: 'highlight',
      text: text.slice(range.start, range.end),
      detection: range.detection,
      isFirstOccurrence,
    });

    cursor = range.end;
  }

  if (cursor < text.length) {
    segments.push({ type: 'plain', text: text.slice(cursor) });
  }

  return segments;
}

interface DocumentViewerProps {
  originalText: string;
  detections: Detection[];
  focusedDetectionId: string | null;
  onDetectionClick: (detectionId: string) => void;
  onDocumentClick: () => void;
}

export function DocumentViewer({
  originalText,
  detections,
  focusedDetectionId,
  onDetectionClick,
  onDocumentClick,
}: DocumentViewerProps) {
  const segments = buildSegments(originalText, detections);

  return (
    <ScrollArea className="h-full">
      <div
        className="p-6 text-sm leading-relaxed"
        style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}
        onClick={onDocumentClick}
      >
        {segments.map((seg, i) => {
          if (seg.type === 'plain') {
            return <span key={i}>{seg.text}</span>;
          }
          return (
            <HighlightSpan
              key={i}
              detection={seg.detection!}
              text={seg.text}
              isFocused={focusedDetectionId === seg.detection!.id}
              isFirstOccurrence={seg.isFirstOccurrence!}
              onClick={onDetectionClick}
            />
          );
        })}
      </div>
    </ScrollArea>
  );
}
