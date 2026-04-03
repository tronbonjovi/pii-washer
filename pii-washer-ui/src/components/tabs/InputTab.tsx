import { useEffect, useRef, useState } from 'react';
import { Loader2, X, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAnalyzeDocument } from '@/hooks/use-analyze-document';
import { useSession } from '@/hooks/use-sessions';
import { useSessionStore } from '@/store/session-store';
import { isAPIError } from '@/types/api';
import { toast } from 'sonner';

function getErrorMessage(error: unknown): string {
  if (isAPIError(error)) {
    if (error.code === 'ENGINE_UNAVAILABLE') {
      return 'The PII detection engine is not available. Make sure the backend is running with spaCy installed.';
    }
    if (error.code === 'FILE_TOO_LARGE') {
      return 'The file is too large. Maximum size is 1 MB.';
    }
    if (error.code === 'UNSUPPORTED_FORMAT') {
      return 'Unsupported file type. Only .txt and .md files are accepted.';
    }
    if (error.code === 'NETWORK_ERROR') {
      return "Unable to connect to the PII Washer backend. Make sure it's running on port 8000.";
    }
    return error.message;
  }
  return 'An unexpected error occurred.';
}

function isFileValidationError(error: unknown): boolean {
  return isAPIError(error) && (error.code === 'FILE_TOO_LARGE' || error.code === 'UNSUPPORTED_FORMAT');
}

export function InputTab() {
  const [text, setText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [loadedSessionKey, setLoadedSessionKey] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const analyzeDocument = useAnalyzeDocument();
  const analyzeDocumentRef = useRef(analyzeDocument);
  analyzeDocumentRef.current = analyzeDocument;
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const resetSession = useSessionStore((s) => s.resetSession);
  const { data: activeSession } = useSession(activeSessionId);

  const draftSession =
    activeSession && activeSession.status === 'user_input' ? activeSession : null;

  useEffect(() => {
    const nextKey = draftSession
      ? `${draftSession.session_id}:${draftSession.updated_at}`
      : null;

    if (nextKey === loadedSessionKey) {
      return;
    }

    setLoadedSessionKey(nextKey);
    analyzeDocumentRef.current.reset();

    if (!draftSession) {
      return;
    }

    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setText(draftSession.original_text);
  }, [draftSession, loadedSessionKey]);

  const hasInput = selectedFile !== null || text.trim().length > 0;
  const isAnalyzing = analyzeDocument.isPending;

  async function handleAnalyze() {
    try {
      let result;
      if (selectedFile) {
        result = await analyzeDocument.mutateAsync({ mode: 'file', file: selectedFile });
      } else if (draftSession && activeSessionId) {
        result = await analyzeDocument.mutateAsync({
          mode: 'existing',
          sessionId: activeSessionId,
        });
      } else {
        result = await analyzeDocument.mutateAsync({ mode: 'text', text });
      }
      const count = result?.detectionCount ?? 0;
      toast.success(`Analysis complete — ${count} detection${count !== 1 ? 's' : ''} found`);
    } catch (err) {
      if (isFileValidationError(err)) {
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
      toast.error(getErrorMessage(err));
    }
  }

  function handleFileSelect(file: File) {
    if (activeSessionId) {
      resetSession();
    }
    setText('');
    setSelectedFile(file);
    analyzeDocument.reset();
  }

  function handleFileRemove() {
    setSelectedFile(null);
    analyzeDocument.reset();
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelect(file);
  }

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Top control row: upload zone (left) + analyze button (right) */}
      <div className="flex items-start justify-between gap-4">
        {/* Upload zone — compact, top-left */}
        <div
          className={[
            'flex items-center gap-2 rounded-md border-2 border-dashed px-3 py-2 cursor-pointer transition-colors select-none text-sm',
            isDragOver
              ? 'border-foreground/50 bg-accent/50'
              : 'border-muted-foreground/30 hover:border-muted-foreground/50',
            isAnalyzing ? 'pointer-events-none opacity-50' : '',
          ].join(' ')}
          onClick={() => !isAnalyzing && fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragEnter={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {selectedFile ? (
            <>
              <span className="text-muted-foreground">📄</span>
              <span className="font-medium max-w-[160px] truncate">{selectedFile.name}</span>
              <button
                type="button"
                className="ml-1 text-muted-foreground hover:text-foreground transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  handleFileRemove();
                }}
                aria-label="Remove file"
              >
                <X className="size-4" />
              </button>
            </>
          ) : (
            <>
              <Upload className="size-4 text-muted-foreground" />
              <span className="text-muted-foreground">Upload .txt / .md</span>
            </>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,text/plain,text/markdown"
          className="hidden"
          onChange={handleFileInputChange}
        />

        {/* Analyze button — top-right */}
        <Button onClick={handleAnalyze} disabled={!hasInput || isAnalyzing}>
          {isAnalyzing ? (
            <>
              <Loader2 className="animate-spin" />
              Analyzing...
            </>
          ) : (
            'Analyze'
          )}
        </Button>
      </div>

      {/* Error message */}
      {analyzeDocument.error && (
        <Alert variant="destructive">
          <AlertDescription className="flex items-start justify-between gap-2">
            <span>{getErrorMessage(analyzeDocument.error)}</span>
            <button
              type="button"
              className="shrink-0 opacity-70 hover:opacity-100 transition-opacity"
              onClick={() => analyzeDocument.reset()}
              aria-label="Dismiss error"
            >
              <X className="size-4" />
            </button>
          </AlertDescription>
        </Alert>
      )}

      {/* Textarea — fills remaining space */}
      <Textarea
        className="flex-1 min-h-[200px] resize-none"
        placeholder="Paste your document here..."
        value={text}
        onChange={(e) => {
          if (draftSession && activeSessionId) {
            resetSession();
          }
          setText(e.target.value);
          if (analyzeDocument.error) analyzeDocument.reset();
        }}
        disabled={selectedFile !== null || isAnalyzing}
      />
    </div>
  );
}
