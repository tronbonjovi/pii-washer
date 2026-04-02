import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { getAppVersion } from '@/api/settings';

interface AboutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AboutDialog({ open, onOpenChange }: AboutDialogProps) {
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    if (open && !version) {
      getAppVersion().then(setVersion).catch(() => {});
    }
  }, [open, version]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader className="items-center text-center">
          <DialogTitle className="text-2xl font-bold">PII Washer</DialogTitle>
          <p className="text-sm text-muted-foreground">
            {version ? `v${version}` : ''}
          </p>
        </DialogHeader>

        <p className="text-center text-sm text-muted-foreground leading-relaxed">
          Local-only PII detection and text sanitization.
          <br />
          Your data never leaves your machine.
        </p>

        <div className="border-t pt-3 mt-1 space-y-2 text-xs text-muted-foreground">
          <div className="flex justify-between">
            <span>License</span>
            <span>AGPL-3.0</span>
          </div>
          <div className="flex justify-between">
            <span>Detection</span>
            <span>Presidio + spaCy</span>
          </div>
          <div className="flex justify-between">
            <span>Source</span>
            <a
              href="https://github.com/tronbonjovi/pii-washer"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-foreground"
            >
              GitHub
            </a>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
