import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { ChevronDown, ChevronUp, Plus } from 'lucide-react';
import type { PIICategory } from '@/types/api';
import { PII_COLORS } from '@/lib/pii-colors';
import { useAddManualDetection } from '@/hooks/use-detections';
import { isAPIError } from '@/types/api';

const CATEGORIES = Object.entries(PII_COLORS).map(([key, val]) => ({
  value: key as PIICategory,
  label: val.label,
}));

interface ManualAddFormProps {
  sessionId: string;
}

export function ManualAddForm({ sessionId }: ManualAddFormProps) {
  const [expanded, setExpanded] = useState(false);
  const [text, setText] = useState('');
  const [category, setCategory] = useState<PIICategory | ''>('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const addMutation = useAddManualDetection(sessionId);

  function handleSubmit() {
    if (!text.trim() || !category) return;
    setSuccessMsg(null);
    setErrorMsg(null);

    addMutation.mutate(
      { textValue: text.trim(), category: category as PIICategory },
      {
        onSuccess: (data) => {
          setSuccessMsg(`Added — found ${data.occurrences_found} occurrence${data.occurrences_found !== 1 ? 's' : ''}`);
          setText('');
          setCategory('');
        },
        onError: (err) => {
          if (isAPIError(err)) {
            if (err.code === 'DUPLICATE_DETECTION') {
              setErrorMsg('This text is already detected in this category');
            } else if (err.code === 'TEXT_NOT_FOUND') {
              setErrorMsg('This text was not found in the document');
            } else {
              setErrorMsg(err.message);
            }
          } else {
            setErrorMsg('Failed to add detection');
          }
        },
      },
    );
  }

  return (
    <div>
      <Separator />
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="flex items-center gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          Add PII
        </span>
        {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          <input
            className="w-full text-sm border rounded px-2 py-1.5 bg-background"
            placeholder="Paste or type PII text..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
          />
          <Select value={category} onValueChange={(v: string) => setCategory(v as PIICategory)}>
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="Select category..." />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIES.map(({ value, label }) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            className="w-full"
            onClick={handleSubmit}
            disabled={!text.trim() || !category || addMutation.isPending}
          >
            {addMutation.isPending ? 'Adding...' : 'Add'}
          </Button>
          {successMsg && <p className="text-xs text-green-600 dark:text-green-400">{successMsg}</p>}
          {errorMsg && <p className="text-xs text-destructive">{errorMsg}</p>}
        </div>
      )}
    </div>
  );
}
