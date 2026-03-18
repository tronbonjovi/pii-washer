import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Detection } from '@/types/api';
import { PII_COLORS } from '@/lib/pii-colors';

interface PlaceholderMapProps {
  detections: Detection[];
}

export function PlaceholderMap({ detections }: PlaceholderMapProps) {
  const confirmed = detections.filter((d) => d.status === 'confirmed');

  return (
    <div className="flex flex-col h-full border-r">
      <div className="p-4 border-b">
        <h3 className="font-semibold text-sm">Placeholder Reference</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          Use these placeholders in your AI prompt — the response should contain them.
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1.5">
          {confirmed.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">
              No confirmed detections.
            </p>
          ) : (
            confirmed.map((det) => {
              const colors = PII_COLORS[det.category];
              return (
                <div
                  key={det.id}
                  className="flex items-start gap-2 rounded-md p-2 hover:bg-muted/40 transition-colors"
                >
                  <Badge
                    className="shrink-0 text-[10px] px-1.5 py-0 mt-0.5"
                    style={{ backgroundColor: colors.badgeBg, color: colors.badgeText }}
                  >
                    {colors.label}
                  </Badge>
                  <div className="min-w-0 flex-1 text-xs space-y-0.5">
                    <p className="font-mono font-medium truncate">{det.placeholder}</p>
                    <p className="text-muted-foreground truncate" title={det.original_value}>
                      {det.original_value}
                    </p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
