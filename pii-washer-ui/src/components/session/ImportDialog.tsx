import { useState, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useImportSession } from '@/hooks/use-sessions';
import { useSessionStore } from '@/store/session-store';
import { tabForStatus } from '@/lib/tab-routing';
import type { APIError } from '@/api/client';
import { toast } from 'sonner';

interface ImportDialogProps {
  onSuccess: () => void;
}

export function ImportDialog({ onSuccess }: ImportDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [readError, setReadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const importSession = useImportSession();
  const setActiveTab = useSessionStore((s) => s.setActiveTab);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setReadError(null);
    importSession.reset();
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
  }

  function handleImport() {
    if (!selectedFile) return;
    setReadError(null);

    const reader = new FileReader();

    reader.onload = () => {
      const text = reader.result as string;

      let parsedStatus: string | undefined;
      try {
        const parsed = JSON.parse(text);
        parsedStatus = parsed?.status;
      } catch {
        setReadError('This file does not contain valid JSON.');
        return;
      }

      importSession.mutate(text, {
        onSuccess: () => {
          setOpen(false);
          setSelectedFile(null);
          setActiveTab(tabForStatus(parsedStatus));
          onSuccess();
          toast.success('Session imported');
        },
        onError: (err) => {
          const apiErr = err as unknown as APIError;
          toast.error(apiErr?.message ?? 'Failed to import session.');
        },
      });
    };

    reader.onerror = () => {
      setReadError('Could not read the file. Please try again.');
    };

    reader.readAsText(selectedFile);
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (!nextOpen) {
      setSelectedFile(null);
      setReadError(null);
      importSession.reset();
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }

  const apiError = importSession.error as APIError | null;
  const errorMessage = readError ?? apiError?.message ?? null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Import
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import session</DialogTitle>
          <DialogDescription>
            Select a JSON file from a previous PII Washer export.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleFileChange}
            className="block w-full text-sm text-foreground
              file:mr-3 file:rounded file:border-0
              file:bg-primary file:px-3 file:py-1.5
              file:text-sm file:font-medium file:text-primary-foreground
              file:cursor-pointer hover:file:bg-primary/90"
          />
        </div>

        {errorMessage && (
          <p className="text-sm text-destructive">{errorMessage}</p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={!selectedFile || importSession.isPending}
          >
            {importSession.isPending ? 'Importing…' : 'Import'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
