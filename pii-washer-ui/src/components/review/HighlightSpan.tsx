import { useEffect, useRef } from 'react';
import type { Detection } from '@/types/api';
import { PII_COLORS } from '@/lib/pii-colors';

interface HighlightSpanProps {
  detection: Detection;
  text: string;
  isFocused: boolean;
  /** Only the first occurrence of a detection should scroll into view */
  isFirstOccurrence: boolean;
  onClick: (detectionId: string) => void;
}

export function HighlightSpan({ detection, text, isFocused, isFirstOccurrence, onClick }: HighlightSpanProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const colors = PII_COLORS[detection.category];
  const isRejected = detection.status === 'rejected';
  const isLowConfidence = detection.confidence < 0.5;

  useEffect(() => {
    if (isFocused && isFirstOccurrence && ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isFocused, isFirstOccurrence]);

  const bg = isFocused ? colors.highlightBgActive : colors.highlightBg;
  const opacity = isRejected ? 0.4 : 1;

  return (
    <span
      ref={ref}
      data-detection-id={detection.id}
      onClick={(e) => {
        // stopPropagation prevents the document container's onClick from clearing focus.
        // This does NOT interfere with text selection — selection uses mouse events,
        // not the click event.
        e.stopPropagation();
        onClick(detection.id);
      }}
      style={{
        backgroundColor: bg,
        opacity,
        cursor: 'pointer',
        borderRadius: '2px',
        paddingInline: '1px',
        borderBottom: isLowConfidence ? '2px dashed currentColor' : undefined,
        outline: isFocused ? `2px solid ${colors.badgeBg}` : undefined,
        outlineOffset: '1px',
        textDecoration: isRejected ? 'line-through' : undefined,
      }}
      title={`${colors.label}: ${detection.original_value}${isLowConfidence ? ' (low confidence)' : ''}`}
    >
      {text}
    </span>
  );
}
