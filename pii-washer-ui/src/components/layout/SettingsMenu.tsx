import { useState } from 'react';
import { Info, Loader2, RefreshCw, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { AboutDialog } from './AboutDialog';
import { checkForUpdates } from '@/api/settings';
import type { UpdateCheckResponse } from '@/types/api';

export function SettingsMenu() {
  const [aboutOpen, setAboutOpen] = useState(false);
  const [updateState, setUpdateState] = useState<
    'idle' | 'loading' | 'done' | 'error'
  >('idle');
  const [updateResult, setUpdateResult] = useState<UpdateCheckResponse | null>(
    null,
  );

  async function handleCheckForUpdates() {
    setUpdateState('loading');
    try {
      const result = await checkForUpdates();
      setUpdateResult(result);
      setUpdateState(result.error ? 'error' : 'done');
    } catch {
      setUpdateState('error');
    }
  }

  function renderUpdateLabel() {
    switch (updateState) {
      case 'loading':
        return (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Checking...
          </>
        );
      case 'done':
        if (updateResult?.update_available) {
          return (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              v{updateResult.latest_version} available
            </>
          );
        }
        return (
          <>
            <RefreshCw className="mr-2 h-4 w-4" />
            You're up to date
          </>
        );
      case 'error':
        return (
          <>
            <RefreshCw className="mr-2 h-4 w-4" />
            Couldn't check for updates
          </>
        );
      default:
        return (
          <>
            <RefreshCw className="mr-2 h-4 w-4" />
            Check for Updates
          </>
        );
    }
  }

  function handleUpdateClick() {
    if (updateState === 'done' && updateResult?.update_available && updateResult.release_url) {
      window.open(updateResult.release_url, '_blank', 'noopener,noreferrer');
    } else if (updateState !== 'loading') {
      handleCheckForUpdates();
    }
  }

  return (
    <>
      <DropdownMenu
        onOpenChange={(open) => {
          if (!open) {
            setUpdateState('idle');
            setUpdateResult(null);
          }
        }}
      >
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            aria-label="Settings"
          >
            <Settings className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => setAboutOpen(true)}>
            <Info className="mr-2 h-4 w-4" />
            About
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              handleUpdateClick();
            }}
          >
            {renderUpdateLabel()}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AboutDialog
        open={aboutOpen}
        onOpenChange={setAboutOpen}
      />
    </>
  );
}
