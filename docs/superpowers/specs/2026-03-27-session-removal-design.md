# Session Removal — Design Spec

**Date:** 2026-03-27
**Goal:** Remove user-facing session management. PII Washer becomes a single-session utility — one active job at a time, "Start Over" to reset.

## Motivation

PII Washer is a simple offline utility, like a calculator for PII. You open it, paste text, clean it, use the cleaned text with AI, repersonalize the response, done. There's no need for session lists, session switching, import/export, or multi-session management. The session infrastructure was over-built for what this tool actually is.

Same input = same output (detection is deterministic), so there's no real need to return to a previous session.

## Design

### User Experience

- App opens to the Input tab, ready to paste
- User pastes text or uploads a file, clicks Analyze
- Workflow proceeds as today: Input -> Review -> Response -> Results
- At any point, user can click "Start Over" to reset and return to Input
- "Start Over" is a simple button in the header — no confirmation dialog, no "are you sure"
- One active job at a time. New paste replaces the old one. No session list, no switching.

### What Gets Removed

**Frontend (delete files):**
- `src/components/session/SessionPanel.tsx` — session sidebar
- `src/components/session/SessionList.tsx` — session list
- `src/components/session/SessionRow.tsx` — session row item
- `src/components/session/SessionActions.tsx` — export/delete dropdown
- `src/components/session/ExportConfirmDialog.tsx` — export dialog
- `src/components/session/DeleteConfirmDialog.tsx` — delete dialog
- `src/components/session/ClearAllConfirmDialog.tsx` — clear all dialog
- `src/components/session/ImportDialog.tsx` — import dialog

**Frontend (modify):**
- `src/store/session-store.ts` — remove `activeSessionId`, `setActiveSession`, `clearActiveSession`; the current session ID is fetched from the backend, not managed as user-facing state
- `src/hooks/use-sessions.ts` — remove `useSessionList`, `useDeleteSession`, `useClearAllSessions`, `useExportSession`, `useImportSession`
- `src/api/sessions.ts` — remove `listSessions`, `deleteSession`, `clearAllSessions`, `exportSession`, `importSession`
- `src/components/layout/Header.tsx` — remove session panel trigger, add "Start Over" button
- Tab components — simplify session ID handling (no more "pick from list")

**Backend (remove endpoints):**
- `GET /sessions` — list all sessions
- `DELETE /sessions` — clear all sessions
- `POST /sessions/import` — import session
- `DELETE /sessions/{id}` — delete individual session
- `GET /sessions/{id}/export` — export session

**Backend (remove methods):**
- `SessionManager`: `list_sessions`, `delete_session`, `clear_all_sessions`, `export_session`, `import_session`
- `TempDataStore`: `list_sessions`, `delete_session`, `clear_all`, `export_session`, `import_session`, `session_count`

**Backend (add):**
- `POST /sessions/reset` — clears current session, returns clean state (the "Start Over" endpoint)

**Backend (keep as-is):**
- `POST /sessions` — create session (now implicitly replaces any existing one)
- `POST /sessions/upload` — upload file (same)
- All workflow endpoints (analyze, depersonalize, response, repersonalize)
- All detection endpoints
- `GET /sessions/{id}` and `GET /sessions/{id}/status` — still needed for the active session
- `TempDataStore.create_session`, `get_session`, `update_session`, `secure_clear`

### How "Start Over" Works

1. User clicks "Start Over" in the header
2. Frontend calls `POST /sessions/reset`
3. Backend calls `secure_clear()` on the store (wipes all in-memory data)
4. Frontend resets to Input tab, clears any cached query data
5. App is back to fresh state, ready for new text

### How Session ID Works Internally

Session IDs still exist as internal plumbing — the API still uses `/sessions/{id}/analyze` etc. The frontend just tracks "the current session" without exposing it as a user concept. When you create a session (paste or upload), the returned ID becomes the implicit current session. There's only ever one.

### File Archiving

Per user preference, removed files are archived (moved to `archive/session-removal/`) rather than deleted from git history. This preserves the code for reference if sessions are ever reintroduced as part of a larger feature revision.

### What This Does NOT Change

- The workflow state machine (user_input -> analyzed -> depersonalized -> awaiting_response -> repersonalized)
- Detection editing (confirm, reject, add manual, edit placeholder)
- The depersonalize/repersonalize flow
- The backend architecture (SessionManager as API boundary, dependency injection, TempDataStore)
- Tests for core workflow behavior (these stay and should still pass)

## Scope

~800-1000 lines removed, ~50-100 lines added (Start Over button + reset endpoint). Net reduction in complexity. Tests for removed features get archived too.
