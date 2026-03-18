import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Copy, Check, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

interface RepersonalizedViewProps {
  repersonalizedText: string;
  unmatchedPlaceholders: string[];
  confirmedCount: number;
  rejectedCount: number;
}

export function RepersonalizedView({
  repersonalizedText,
  unmatchedPlaceholders,
  confirmedCount,
  rejectedCount,
}: RepersonalizedViewProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(repersonalizedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Copied to clipboard');
  }

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Restored Text</h2>
          <p className="text-sm text-muted-foreground">
            {confirmedCount} placeholder{confirmedCount !== 1 ? 's' : ''} restored
            {rejectedCount > 0 && `, ${rejectedCount} rejected (left in place)`}
          </p>
        </div>
        <Button onClick={handleCopy} variant="outline" className="shrink-0 flex items-center gap-2">
          {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
          {copied ? 'Copied!' : 'Copy'}
        </Button>
      </div>

      {/* Unmatched placeholder warnings */}
      {unmatchedPlaceholders.length > 0 && (
        <div className="rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400 mb-2">
            <AlertTriangle className="h-4 w-4" />
            {unmatchedPlaceholders.length} placeholder{unmatchedPlaceholders.length !== 1 ? 's were' : ' was'} not found in the response
          </div>
          <div className="flex flex-wrap gap-1">
            {unmatchedPlaceholders.map((ph) => (
              <Badge key={ph} variant="outline" className="font-mono text-[10px] text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-700">
                {ph}
              </Badge>
            ))}
          </div>
          <p className="text-xs text-amber-600 dark:text-amber-500 mt-2">
            These placeholders were confirmed but the AI response did not use them. The original values were not restored.
          </p>
        </div>
      )}

      {/* Restored text */}
      <div
        className="flex-1 min-h-0 overflow-auto rounded-md border bg-muted/30 p-4 text-sm"
        style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}
      >
        {repersonalizedText}
      </div>
    </div>
  );
}
