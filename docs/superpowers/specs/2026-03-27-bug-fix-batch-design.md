# Bug Fix Batch — Design Spec

**Date:** 2026-03-27
**Scope:** 6 non-session bugs (4 session-related bugs deferred — will be resolved by upcoming session removal)

## Context

Code audit identified 10 bugs across backend and frontend. 4 are session management bugs (#2 TOCTOU race, #4 stale closure on delete, #6 import status defaults, #10 orphaned sessions) — these will be eliminated when session management is removed in a follow-up milestone. This spec covers the remaining 6 bugs that affect the core workflow.

## Execution Strategy

Two parallel agents: one backend (Python), one frontend (TypeScript). Each writes tests first (TDD), then implements. Code review + full test suite after both complete.

---

## Backend Fixes (3 bugs)

### Bug #1: Upload metadata not persisted
**File:** `pii_washer/api/router.py:140-144`
**Problem:** Upload endpoint calls `sm.load_text()` which hardcodes `source_format="paste"` and `filename=None`. The endpoint then sets correct values on a deep copy that is immediately discarded. Every subsequent read shows `"paste"` format and no filename.
**Fix:** Add a `load_uploaded_content(text, source_format, filename)` method to `SessionManager` that passes the real metadata through to `store.create_session()`. Update the upload endpoint to call this instead of `load_text()`.

### Bug #5: Full file buffered before size check + limit mismatch
**File:** `pii_washer/api/router.py:116-124`
**Problem:** `await file.read()` loads entire upload before checking size. Router cap is 10MB, DocumentLoader cap is 1MB — the 1MB check never fires for uploads.
**Fix:** Read in chunks up to 1MB limit, bail early if exceeded. Use `DocumentLoader.MAX_FILE_SIZE` as single source of truth. Remove the separate `MAX_UPLOAD_SIZE_BYTES` constant.

### Bug #7: City lookup performance — O(n*m) regex
**File:** `pii_washer/pii_detection_engine.py:667-669`
**Problem:** 200 separate `re.search()` calls (uncompiled) per 5-digit number found in text.
**Fix:** Pre-compile a single alternation regex at `__init__` time: `re.compile(r"\b(?:city1|city2|...)\b")`. Use one `.search()` call instead of 200.

---

## Frontend Fixes (3 bugs)

### Bug #3: setState during render in ResponseTab
**File:** `pii-washer-ui/src/components/tabs/ResponseTab.tsx:29-41`
**Problem:** `setSessionSnapshot()` and `setResponseText()` called directly in render body. Risks infinite re-render loops in React 19 concurrent mode.
**Fix:** Move snapshot sync into a `useEffect` with `snapshotKey` as dependency.

### Bug #8: Blob URL revoked before download starts
**File:** `pii-washer-ui/src/components/session/SessionActions.tsx:125-127`
**Problem:** `URL.revokeObjectURL(url)` called synchronously after `anchor.click()`. Download can silently fail.
**Fix:** Wrap revocation in `setTimeout(() => URL.revokeObjectURL(url), 100)`.

### Bug #9: "Confirm All" ignores can_edit_detections
**File:** `pii-washer-ui/src/components/review/BulkActions.tsx:50-55`
**Problem:** Button disabled only when `pending_count === 0`. Clickable in states where edits should be locked.
**Fix:** Add `!sessionStatus.can_edit_detections` to the `disabled` prop.

---

## Deferred (removed by session simplification)

- Bug #2: TOCTOU race on detection IDs — session management plumbing
- Bug #4: Stale closure in useDeleteSession — session delete feature
- Bug #6: Import defaults missing status — session import feature
- Bug #10: Orphaned sessions on analyze failure — session lifecycle

---

## Verification

After all fixes:
1. `pytest` — full backend test suite passes
2. `npm run build` — frontend compiles clean
3. `npm run lint` — no new lint errors
4. Code review agent pass
