import { useEffect, useRef, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Check, X, Pencil, AlertTriangle } from 'lucide-react';
import type { Detection, DetectionStatus } from '@/types/api';
import { PII_COLORS } from '@/lib/pii-colors';
import { useUpdateDetectionStatus } from '@/hooks/use-detections';
import { useEditPlaceholder } from '@/hooks/use-detections';
import { isAPIError } from '@/types/api';

interface DetectionCardProps {
  detection: Detection;
  sessionId: string;
  isFocused: boolean;
  onClick: (detectionId: string) => void;
}

export function DetectionCard({ detection, sessionId, isFocused, onClick }: DetectionCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const colors = PII_COLORS[detection.category];
  const isLowConfidence = detection.confidence < 0.5;

  const updateStatus = useUpdateDetectionStatus(sessionId);
  const editPlaceholder = useEditPlaceholder(sessionId);

  const [editingPlaceholder, setEditingPlaceholder] = useState(false);
  const [placeholderDraft, setPlaceholderDraft] = useState('');
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    if (isFocused && ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [isFocused]);

  function handleStatusToggle(newStatus: DetectionStatus) {
    const next = detection.status === newStatus ? 'pending' : newStatus;
    updateStatus.mutate({ detectionId: detection.id, status: next });
  }

  function handleSavePlaceholder() {
    setEditError(null);
    editPlaceholder.mutate(
      { detectionId: detection.id, placeholder: placeholderDraft },
      {
        onSuccess: () => setEditingPlaceholder(false),
        onError: (err) => {
          setEditError(isAPIError(err) ? err.message : 'Failed to save placeholder');
        },
      },
    );
  }

  const focusStyle = isFocused
    ? { borderColor: colors.badgeBg, boxShadow: `0 0 0 2px ${colors.highlightBgActive}` }
    : {};

  const cardOpacity = detection.status === 'rejected' ? 'opacity-50' : '';

  return (
    <div ref={ref} data-detection-id={detection.id}>
      <Card
        className={`cursor-pointer transition-all duration-150 ${cardOpacity}`}
        style={focusStyle}
        onClick={() => onClick(detection.id)}
      >
        <CardContent className="p-3 space-y-2">
          {/* Header row: badge + confidence + source */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <Badge style={{ backgroundColor: colors.badgeBg, color: colors.badgeText }} className="text-[10px]">
              {colors.label}
            </Badge>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              {isLowConfidence && (
                <span title="Low confidence"><AlertTriangle className="h-3 w-3 text-amber-500" /></span>
              )}
              <span>{Math.round(detection.confidence * 100)}%</span>
              {detection.source === 'manual' && (
                <span className="text-[10px] bg-muted px-1 rounded">manual</span>
              )}
            </div>
          </div>

          {/* Original value */}
          <p className="text-sm font-medium truncate" title={detection.original_value}>
            {detection.original_value}
          </p>

          {/* Placeholder row */}
          <div className="flex items-center gap-1">
            {editingPlaceholder ? (
              <div className="flex items-center gap-1 w-full" onClick={(e) => e.stopPropagation()}>
                <input
                  autoFocus
                  className="flex-1 text-xs border rounded px-1.5 py-0.5 bg-background"
                  value={placeholderDraft}
                  onChange={(e) => setPlaceholderDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSavePlaceholder();
                    if (e.key === 'Escape') setEditingPlaceholder(false);
                  }}
                />
                <Button size="sm" className="h-5 px-2 text-[10px]" onClick={handleSavePlaceholder} disabled={editPlaceholder.isPending}>
                  Save
                </Button>
                <Button size="sm" variant="ghost" className="h-5 px-2 text-[10px]" onClick={() => setEditingPlaceholder(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <button
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                onClick={(e) => {
                  e.stopPropagation();
                  setPlaceholderDraft(detection.placeholder);
                  setEditingPlaceholder(true);
                }}
                title="Edit placeholder"
              >
                <span className="font-mono">{detection.placeholder}</span>
                <Pencil className="h-2.5 w-2.5" />
              </button>
            )}
          </div>
          {editError && <p className="text-[10px] text-destructive">{editError}</p>}

          {/* Status controls */}
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <Button
              size="sm"
              variant={detection.status === 'confirmed' ? 'default' : 'outline'}
              className="h-6 px-2 text-[10px] flex items-center gap-0.5"
              onClick={() => handleStatusToggle('confirmed')}
              disabled={updateStatus.isPending}
            >
              <Check className="h-3 w-3" />
              Confirm
            </Button>
            <Button
              size="sm"
              variant={detection.status === 'rejected' ? 'destructive' : 'outline'}
              className="h-6 px-2 text-[10px] flex items-center gap-0.5"
              onClick={() => handleStatusToggle('rejected')}
              disabled={updateStatus.isPending}
            >
              <X className="h-3 w-3" />
              Reject
            </Button>
          </div>
          {updateStatus.isError && (
            <p className="text-[10px] text-destructive">
              {isAPIError(updateStatus.error) ? updateStatus.error.message : 'Update failed'}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
