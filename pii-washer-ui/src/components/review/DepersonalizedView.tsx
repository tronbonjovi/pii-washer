import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Copy, Check, ArrowRight, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { useSessionStore } from '@/store/session-store';

interface DepersonalizedViewProps {
  depersonalizedText: string;
  confirmedCount: number;
  rejectedCount: number;
  onContinue: () => void;
}

export function DepersonalizedView({
  depersonalizedText,
  confirmedCount,
  rejectedCount,
  onContinue,
}: DepersonalizedViewProps) {
  const [copied, setCopied] = useState(false);
  const setActiveTab = useSessionStore((s) => s.setActiveTab);

  async function handleCopy() {
    await navigator.clipboard.writeText(depersonalizedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Copied to clipboard');
  }

  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Clean Text Ready</h2>
          <p className="text-sm text-muted-foreground">
            {confirmedCount} item{confirmedCount !== 1 ? 's' : ''} confirmed, {rejectedCount} rejected
          </p>
        </div>
        <Button onClick={handleCopy} variant="outline" className="flex items-center gap-2">
          {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
          {copied ? 'Copied!' : 'Copy to Clipboard'}
        </Button>
      </div>

      <div
        className="flex-1 min-h-0 overflow-auto rounded-md border bg-muted/30 p-4 text-sm"
        style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}
      >
        {depersonalizedText.split(/(\[[A-Za-z_]+_\d+\])/g).map((part, i) => {
          const isPlaceholder = /^\[[A-Za-z_]+_\d+\]$/.test(part);
          return isPlaceholder ? (
            <span key={i} className="font-mono bg-yellow-100 dark:bg-yellow-900/40 px-0.5 rounded text-yellow-800 dark:text-yellow-200">
              {part}
            </span>
          ) : (
            <span key={i}>{part}</span>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-4 border-t pt-4">
        <Button variant="outline" size="sm" onClick={() => setActiveTab('input')} className="flex items-center gap-1.5 shrink-0">
          <ArrowLeft className="h-3.5 w-3.5" />
          Input
        </Button>
        <p className="text-sm text-muted-foreground text-center">
          Text is ready. Copy it and paste it into your AI tool, then continue.
        </p>
        <Button onClick={onContinue} className="flex items-center gap-2 shrink-0">
          Response
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
