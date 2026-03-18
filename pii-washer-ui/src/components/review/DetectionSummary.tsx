import { Badge } from '@/components/ui/badge';
import type { Detection, PIICategory } from '@/types/api';
import { PII_COLORS } from '@/lib/pii-colors';

interface DetectionSummaryProps {
  detections: Detection[];
}

export function DetectionSummary({ detections }: DetectionSummaryProps) {
  const pending = detections.filter((d) => d.status === 'pending').length;
  const confirmed = detections.filter((d) => d.status === 'confirmed').length;
  const rejected = detections.filter((d) => d.status === 'rejected').length;

  // Count by category
  const byCat = detections.reduce<Partial<Record<PIICategory, number>>>((acc, d) => {
    acc[d.category] = (acc[d.category] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-3 border-b space-y-2">
      <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
        <span className="font-medium text-foreground">{detections.length} detections</span>
        <span className="text-yellow-600 dark:text-yellow-400">{pending} pending</span>
        <span className="text-green-600 dark:text-green-400">{confirmed} confirmed</span>
        <span className="text-muted-foreground line-through">{rejected} rejected</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {(Object.entries(byCat) as [PIICategory, number][]).map(([cat, count]) => {
          const colors = PII_COLORS[cat];
          return (
            <Badge
              key={cat}
              style={{ backgroundColor: colors.badgeBg, color: colors.badgeText }}
              className="text-[10px] px-1.5 py-0"
            >
              {colors.label} ×{count}
            </Badge>
          );
        })}
      </div>
    </div>
  );
}
