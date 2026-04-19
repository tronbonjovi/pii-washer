# Milestone 2 — Correctness Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five concrete correctness issues in the backend and frontend — error classification fragility, a cross-layer constant leak, a state-sync bug in `ResponseTab`, a nuclear cache clear, and three duplicated empty-state panels.

**Architecture:**
- Backend: introduce a small hierarchy of custom exception classes (`APIError` → `InvalidStateError`, `DetectionNotFoundError`, `DuplicateDetectionError`, `TextNotFoundError`) that each carry their own HTTP status + error code. The error-response handler in `api/errors.py` matches on `isinstance` first and falls back to the legacy string-matcher for any un-migrated callsites. Move `MAX_FILE_SIZE` from `DocumentLoader` class attribute to `api/config.py` as a module constant shared by both router and loader.
- Frontend: include the response-text content directly in `ResponseTab`'s `snapshotKey` so server-side changes trigger local state re-sync. Replace `queryClient.clear()` in `useResetSession` with explicit per-key invalidation. Extract the three duplicated "No document loaded" panels into a single `<NoSessionAlert>` component.

**Tech Stack:** Python 3.11–3.13, FastAPI, pytest. React 19, TypeScript, TanStack React Query, Zustand, vitest + @testing-library/react.

---

## Pre-flight

Work continues on `main`. Ensure working tree is clean and milestone 1 has landed.

- [ ] **Run baseline tests** (should match milestone 1 final state)

Run: `.venv/Scripts/python.exe -m pytest -q -m "not integration"`
Expected: `439 passed, 4 deselected`

Run: `npm --prefix pii-washer-ui run build && npm --prefix pii-washer-ui run lint && npm --prefix pii-washer-ui run test`
Expected: build OK, lint OK, tests 8 passed.

---

## Task 1: Custom exception classes for API errors

**Files:**
- Create: `pii_washer/api/exceptions.py` — four exception classes
- Modify: `pii_washer/api/errors.py` — match by type first
- Modify: `pii_washer/session_manager.py` — raise specific exception types at known sites
- Create: `pii_washer/tests/test_api_exceptions.py` — unit-test each class and the classifier

Rationale: `classify_value_error()` string-matches on exception messages (`"expected '"`, `"Detection not found:"`, `"already detected as"`, `"was not found in the document"`) to map `ValueError` → HTTP status. Any rephrasing of those messages silently breaks routing; no unit tests guard it. The fix: subclass `ValueError` (so existing `except ValueError` blocks still catch them) and attach `.http_status` + `.error_code` to each subclass. Legacy string-matching stays as a fallback so we don't have to touch every callsite in one commit.

- [ ] **Step 1: Create the exception module**

Create `pii_washer/api/exceptions.py`:

```python
"""Custom API exception classes.

Each class extends ValueError (so existing `except ValueError` handlers
still catch them) and carries its HTTP status + machine-readable error
code. The api/errors.py response handler matches by type first, falling
back to string-matching for un-migrated ValueError raise sites.
"""


class APIError(ValueError):
    """Base class for API-handled exceptions.

    Subclasses set `http_status` and `error_code` as class attributes.
    """

    http_status: int = 422
    error_code: str = "VALIDATION_ERROR"


class InvalidStateError(APIError):
    """Raised when an operation is attempted in the wrong session state."""

    http_status = 409
    error_code = "INVALID_STATE"


class DetectionNotFoundError(APIError):
    """Raised when a detection id doesn't exist in the session."""

    http_status = 404
    error_code = "NOT_FOUND"


class DuplicateDetectionError(APIError):
    """Raised when a manual detection duplicates an existing one."""

    http_status = 409
    error_code = "DUPLICATE_DETECTION"


class TextNotFoundError(APIError):
    """Raised when a text value doesn't appear in the document."""

    http_status = 422
    error_code = "TEXT_NOT_FOUND"
```

- [ ] **Step 2: Write the unit tests first (TDD)**

Create `pii_washer/tests/test_api_exceptions.py`:

```python
"""Unit tests for custom API exception classes and the error-response
handler's type-based classification."""

import pytest

from pii_washer.api.errors import value_error_response
from pii_washer.api.exceptions import (
    APIError,
    DetectionNotFoundError,
    DuplicateDetectionError,
    InvalidStateError,
    TextNotFoundError,
)


class TestExceptionClassAttributes:
    def test_invalid_state_error_attributes(self):
        exc = InvalidStateError("test")
        assert exc.http_status == 409
        assert exc.error_code == "INVALID_STATE"
        assert isinstance(exc, ValueError)

    def test_detection_not_found_attributes(self):
        exc = DetectionNotFoundError("test")
        assert exc.http_status == 404
        assert exc.error_code == "NOT_FOUND"
        assert isinstance(exc, ValueError)

    def test_duplicate_detection_attributes(self):
        exc = DuplicateDetectionError("test")
        assert exc.http_status == 409
        assert exc.error_code == "DUPLICATE_DETECTION"
        assert isinstance(exc, ValueError)

    def test_text_not_found_attributes(self):
        exc = TextNotFoundError("test")
        assert exc.http_status == 422
        assert exc.error_code == "TEXT_NOT_FOUND"
        assert isinstance(exc, ValueError)

    def test_base_api_error_defaults(self):
        exc = APIError("test")
        assert exc.http_status == 422
        assert exc.error_code == "VALIDATION_ERROR"


class TestValueErrorResponseTypeBased:
    """Verify the response handler uses isinstance checks for APIError."""

    def test_invalid_state_error_returns_409(self):
        resp = value_error_response(InvalidStateError("bad state"))
        assert resp.status_code == 409
        body = _body(resp)
        assert body["error"]["code"] == "INVALID_STATE"
        assert body["error"]["message"] == "bad state"

    def test_detection_not_found_returns_404(self):
        resp = value_error_response(DetectionNotFoundError("det_xyz"))
        assert resp.status_code == 404
        assert _body(resp)["error"]["code"] == "NOT_FOUND"

    def test_duplicate_detection_returns_409(self):
        resp = value_error_response(DuplicateDetectionError("dup"))
        assert resp.status_code == 409
        assert _body(resp)["error"]["code"] == "DUPLICATE_DETECTION"

    def test_text_not_found_returns_422(self):
        resp = value_error_response(TextNotFoundError("missing"))
        assert resp.status_code == 422
        assert _body(resp)["error"]["code"] == "TEXT_NOT_FOUND"

    def test_plain_value_error_falls_back_to_validation_error(self):
        """Un-migrated ValueErrors still default to 422 VALIDATION_ERROR."""
        resp = value_error_response(ValueError("random bad input"))
        assert resp.status_code == 422
        assert _body(resp)["error"]["code"] == "VALIDATION_ERROR"

    def test_legacy_string_match_state_error_still_works(self):
        """Backward-compat: raise ValueError with 'expected' wording → 409."""
        resp = value_error_response(
            ValueError("session status is 'foo', expected 'bar'")
        )
        assert resp.status_code == 409


def _body(resp):
    import json
    return json.loads(bytes(resp.body).decode("utf-8"))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest pii_washer/tests/test_api_exceptions.py -v`
Expected: FAIL — `ImportError` or assertion failures on the `TestValueErrorResponseTypeBased` class (the handler doesn't yet know about the new exception types).

Note: The `TestExceptionClassAttributes` tests may pass once Step 1 is done (pure class definitions). The type-based handler tests fail until Step 4.

- [ ] **Step 4: Update `errors.py` to match on type first**

Replace `pii_washer/api/errors.py` entirely with:

```python
import logging

from fastapi.responses import JSONResponse

from .exceptions import APIError

logger = logging.getLogger("pii_washer")


def _error_body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def classify_value_error(message: str) -> tuple[int, str]:
    """Legacy classifier for plain ValueErrors. Kept as a fallback so raise
    sites that haven't yet migrated to specific APIError subclasses still get
    the right HTTP status. New code should raise a concrete APIError subclass
    from pii_washer.api.exceptions instead."""
    if "session status is" in message or "expected '" in message:
        return 409, "INVALID_STATE"
    if "Detection not found:" in message:
        return 404, "NOT_FOUND"
    if "already detected as" in message:
        return 409, "DUPLICATE_DETECTION"
    if "was not found in the document" in message:
        return 422, "TEXT_NOT_FOUND"
    return 422, "VALIDATION_ERROR"


def key_error_response(exc: KeyError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=_error_body("NOT_FOUND", str(exc).strip("'")),
    )


def value_error_response(exc: ValueError) -> JSONResponse:
    message = str(exc)
    # Prefer type-based classification. Any APIError subclass carries its own
    # status + code, so we don't need to match on message wording.
    if isinstance(exc, APIError):
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_body(exc.error_code, message),
        )
    status_code, code = classify_value_error(message)
    return JSONResponse(
        status_code=status_code,
        content=_error_body(code, message),
    )


def runtime_error_response(exc: RuntimeError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=_error_body("ENGINE_UNAVAILABLE", str(exc)),
    )


def server_error_response(exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_body("SERVER_ERROR", "An unexpected error occurred"),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest pii_washer/tests/test_api_exceptions.py -v`
Expected: PASS — all class attribute tests and all type-based response handler tests pass.

- [ ] **Step 6: Migrate `session_manager.py` raise sites to typed exceptions**

In `pii_washer/session_manager.py`, update the top imports:

Find the existing import block at the top of the file and add this line after the last existing import in the block:

```python
from pii_washer.api.exceptions import (
    DetectionNotFoundError,
    DuplicateDetectionError,
    InvalidStateError,
    TextNotFoundError,
)
```

Then update raise sites. Use find-and-replace carefully — there are several `raise ValueError` calls but only the specific message patterns should change.

**State transition errors → `InvalidStateError`:** any `raise ValueError(...)` whose message contains `"expected '"` (typically `f"... status is '{status}', expected '{expected}'"`). These appear at these line numbers (subject to drift — search by pattern, not line number): 101, 133, 153, 172, 311, 332, 347. For each, change `raise ValueError(` to `raise InvalidStateError(`.

Example:
```python
# Before:
raise ValueError(
    f"Cannot analyze: session status is '{status}', expected 'user_input'"
)
# After:
raise InvalidStateError(
    f"Cannot analyze: session status is '{status}', expected 'user_input'"
)
```

**Detection-not-found errors → `DetectionNotFoundError`:** lines 147 and 200. Messages begin with `"Detection not found:"`.

Example:
```python
# Before:
raise ValueError(f"Detection not found: {detection_id}")
# After:
raise DetectionNotFoundError(f"Detection not found: {detection_id}")
```

**Duplicate detection → `DuplicateDetectionError`:** line ~238. Message contains `"already detected as"`.

Example:
```python
# Before:
raise ValueError(
    f"'{text_value}' is already detected as {category}. "
    "You can confirm or edit it in the detection list."
)
# After:
raise DuplicateDetectionError(
    f"'{text_value}' is already detected as {category}. "
    "You can confirm or edit it in the detection list."
)
```

**Text-not-found → `TextNotFoundError`:** line ~252. Message contains `"was not found in the document"`.

Example:
```python
# Before:
raise ValueError(
    f"'{text_value}' was not found in the document text."
)
# After:
raise TextNotFoundError(
    f"'{text_value}' was not found in the document text."
)
```

Leave all other `raise ValueError` calls unchanged — they're generic validation errors that correctly map to 422 VALIDATION_ERROR via the default path.

- [ ] **Step 7: Run full test suite**

Run: `.venv/Scripts/python.exe -m pytest -q -m "not integration"`
Expected: all tests pass, including the existing integration-style tests in `test_api.py` that exercise the HTTP error paths (they continue to pass because each APIError subclass still extends ValueError and produces the same HTTP status + error code as before).

- [ ] **Step 8: Commit**

```bash
git add pii_washer/api/exceptions.py pii_washer/api/errors.py pii_washer/session_manager.py pii_washer/tests/test_api_exceptions.py
git commit -m "refactor(api): typed exceptions instead of string-matched ValueErrors"
```

---

## Task 2: Move `MAX_FILE_SIZE` from `DocumentLoader` to `config.py`

**Files:**
- Modify: `pii_washer/api/config.py` — add module-level `MAX_FILE_SIZE` constant
- Modify: `pii_washer/document_loader.py` — import from config, drop class attribute
- Modify: `pii_washer/api/router.py` — import from config, drop `DocumentLoader.MAX_FILE_SIZE` reference

Rationale: Router currently imports `DocumentLoader` just to read its `MAX_FILE_SIZE` class attribute (`router.py:144`). The router doesn't need the class, only the constant. Moving the constant to `api/config.py` (alongside `ALLOWED_EXTENSIONS`, `BINARY_FORMATS`) eliminates the cross-layer coupling and co-locates all file-size/format policy in one place.

- [ ] **Step 1: Add the constant to `config.py`**

In `pii_washer/api/config.py`, add this line near the other size/format constants (after `BINARY_FORMATS`):

```python
MAX_FILE_SIZE = 1_048_576  # 1 MB in bytes — shared by router upload check and DocumentLoader
```

- [ ] **Step 2: Update `document_loader.py`**

In `pii_washer/document_loader.py`:

Find the class-level constant:
```python
    MAX_FILE_SIZE = 1_048_576  # 1 MB in bytes
```

Delete that line.

At the top of the file, add the import (alongside existing imports):
```python
from pii_washer.api.config import MAX_FILE_SIZE
```

Find every internal reference to `self.MAX_FILE_SIZE` or `DocumentLoader.MAX_FILE_SIZE` inside the module and change it to `MAX_FILE_SIZE`. The grep from pre-planning showed the references are at lines 38 and 130.

At line 38 (inside `load_file`):
```python
# Before:
if file_size > self.MAX_FILE_SIZE:
# After:
if file_size > MAX_FILE_SIZE:
```

At line 130 (a getter method):
```python
# Before:
return self.MAX_FILE_SIZE
# After:
return MAX_FILE_SIZE
```

- [ ] **Step 3: Update `router.py`**

In `pii_washer/api/router.py`:

Update the imports — change the `config` import to include `MAX_FILE_SIZE`:
```python
# Before:
from .config import ALLOWED_EXTENSIONS, BINARY_FORMATS, get_app_version
# After:
from .config import ALLOWED_EXTENSIONS, BINARY_FORMATS, MAX_FILE_SIZE, get_app_version
```

At router.py line 144, replace:
```python
max_size = DocumentLoader.MAX_FILE_SIZE
```
with:
```python
max_size = MAX_FILE_SIZE
```

The `from pii_washer.document_loader import DocumentLoader` import at line 7 is used elsewhere (or not — verify). If `DocumentLoader` is no longer referenced anywhere in `router.py` after this change, remove the import. Run `grep -n "DocumentLoader" pii_washer/api/router.py` to confirm.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest -q -m "not integration"`
Expected: all tests pass. The upload-size tests should be untouched because the constant value is identical.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/api/config.py pii_washer/document_loader.py pii_washer/api/router.py
git commit -m "refactor: move MAX_FILE_SIZE to config.py (one source for upload policy)"
```

---

## Task 3: Fix `ResponseTab` snapshotKey to include `response_text`

**Files:**
- Modify: `pii-washer-ui/src/components/tabs/ResponseTab.tsx:29-47` — derive snapshotKey from response_text content too
- Create: `pii-washer-ui/src/components/tabs/__tests__/ResponseTab.test.tsx` — component test for state sync

Rationale: Today, `snapshotKey` is `${session_id}:(awaiting-response|loaded)`. If the server-side `response_text` changes while the session stays in `awaiting_response` (e.g. the user loads a response, cancels, loads a different one before repersonalizing), the local `responseText` state never re-syncs because the ref-guarded effect sees the same `snapshotKey`.

Fix: include the response text's length + first-128-char prefix in the snapshotKey — enough to detect changes without storing the full text in a key. Full text in the key is also fine but bloats React internals; prefix+length is equivalent for cache-bust purposes and avoids edge cases with very large responses.

- [ ] **Step 1: Write the failing test first**

Create `pii-washer-ui/src/components/tabs/__tests__/ResponseTab.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ResponseTab } from '../ResponseTab';
import { useSessionStore } from '@/store/session-store';
import * as sessionsApi from '@/api/sessions';
import type { Session } from '@/types/api';

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function makeSession(overrides: Partial<Session> = {}): Session {
  return {
    session_id: 'sess-1',
    status: 'awaiting_response',
    source_format: 'text',
    original_text: 'original',
    depersonalized_text: '[Person_1]',
    response_text: 'first response [Person_1]',
    repersonalized_text: null,
    pii_detections: [],
    unmatched_placeholders: [],
    created_at: '2026-04-18T00:00:00Z',
    updated_at: '2026-04-18T00:00:00Z',
    ...overrides,
  };
}

describe('ResponseTab state sync', () => {
  beforeEach(() => {
    useSessionStore.setState({ activeSessionId: 'sess-1', activeTab: 'response' });
    vi.restoreAllMocks();
  });

  it('syncs textarea when server response_text changes while status stays awaiting_response', async () => {
    const getSession = vi.spyOn(sessionsApi, 'getSession');
    const getSessionStatus = vi.spyOn(sessionsApi, 'getSessionStatus');
    getSession.mockResolvedValueOnce(makeSession({ response_text: 'first response [Person_1]' }));
    getSessionStatus.mockResolvedValue({
      status: 'awaiting_response',
      pending_count: 0,
      confirmed_count: 1,
      rejected_count: 0,
      can_depersonalize: false,
    } as never);

    const { rerender } = render(<ResponseTab />, { wrapper });

    const textarea = await screen.findByPlaceholderText(/Paste the AI response/i);
    expect((textarea as HTMLTextAreaElement).value).toBe('first response [Person_1]');

    // Server now returns a different response_text, same session, same status
    getSession.mockResolvedValueOnce(makeSession({ response_text: 'SECOND response [Person_1]' }));
    rerender(<ResponseTab />);

    // Wait for the refetch to propagate
    await vi.waitFor(() => {
      expect((screen.getByPlaceholderText(/Paste the AI response/i) as HTMLTextAreaElement).value).toBe(
        'SECOND response [Person_1]',
      );
    });
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm --prefix pii-washer-ui run test -- ResponseTab.test`
Expected: FAIL — the assertion on the second response_text will fail because the textarea remains at `"first response [Person_1]"`.

- [ ] **Step 3: Update the snapshotKey derivation in `ResponseTab.tsx`**

In `pii-washer-ui/src/components/tabs/ResponseTab.tsx`, replace lines 29-33 (the `snapshotKey` calculation) with a version that incorporates response_text:

```tsx
  const snapshotKey = session
    ? `${session.session_id}:${session.status}:${responseTextKey(session.response_text)}`
    : activeSessionId
      ? `loading:${activeSessionId}`
      : null;
```

Add a small helper at the top of the file (below imports, above the component):

```tsx
function responseTextKey(text: string | null | undefined): string {
  if (!text) return 'empty';
  // Fingerprint = length + prefix — enough to detect content changes without
  // storing the full text in a React key.
  return `${text.length}:${text.slice(0, 128)}`;
}
```

The key no longer needs the conditional `status === 'awaiting_response' && !!response_text ? 'awaiting-response' : 'loaded'` logic — including `session.status` and the response text fingerprint together gives strictly more precise invalidation.

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm --prefix pii-washer-ui run test -- ResponseTab.test`
Expected: PASS — textarea updates to the new response_text.

- [ ] **Step 5: Run the full frontend test + build**

Run: `npm --prefix pii-washer-ui run build && npm --prefix pii-washer-ui run lint && npm --prefix pii-washer-ui run test`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add pii-washer-ui/src/components/tabs/ResponseTab.tsx pii-washer-ui/src/components/tabs/__tests__/ResponseTab.test.tsx
git commit -m "fix(ui): ResponseTab resyncs textarea when server response_text changes"
```

---

## Task 4: Replace `queryClient.clear()` with targeted invalidation in `useResetSession`

**Files:**
- Modify: `pii-washer-ui/src/hooks/use-sessions.ts:53-64` — swap `clear()` for specific invalidations

Rationale: `queryClient.clear()` nukes the ENTIRE React Query cache on reset, including unrelated queries (health check, settings, updates). Targeted invalidation of the three session-related key prefixes — `['session']`, `['sessionStatus']`, `['sessions']` — is equivalent for the reset use case and preserves everything else.

- [ ] **Step 1: Update `useResetSession`**

In `pii-washer-ui/src/hooks/use-sessions.ts`, replace the `useResetSession` function (currently lines 53-64):

```ts
export function useResetSession() {
  const queryClient = useQueryClient();
  const resetStore = useSessionStore((s) => s.resetSession);

  return useMutation({
    mutationFn: resetSession,
    onSuccess: () => {
      // Targeted invalidation — only session-scoped queries. Preserves
      // health, settings, and other unrelated caches.
      queryClient.invalidateQueries({ queryKey: ['session'] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus'] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      resetStore();
    },
  });
}
```

Note: `invalidateQueries({ queryKey: ['session'] })` invalidates all queries whose key starts with `['session', ...]` by default (prefix match). Same for the other two.

- [ ] **Step 2: Run frontend checks**

Run: `npm --prefix pii-washer-ui run build && npm --prefix pii-washer-ui run lint && npm --prefix pii-washer-ui run test`
Expected: all green.

- [ ] **Step 3: Commit**

```bash
git add pii-washer-ui/src/hooks/use-sessions.ts
git commit -m "fix(ui): useResetSession targets session keys instead of clearing whole cache"
```

---

## Task 5: Extract `<NoSessionAlert>` component and dedupe across tabs

**Files:**
- Create: `pii-washer-ui/src/components/layout/NoSessionAlert.tsx`
- Modify: `pii-washer-ui/src/components/tabs/ReviewTab.tsx:26-33` — use component
- Modify: `pii-washer-ui/src/components/tabs/ResponseTab.tsx:49-59` — use component
- Modify: `pii-washer-ui/src/components/tabs/ResultsTab.tsx:15-23` — use component

Rationale: Three tabs render an identical 6-line panel whenever `activeSessionId` is null: "No document loaded" + "Go to the Input tab to get started." + button. Extract once. Changes to copy or design land in one place.

- [ ] **Step 1: Create the component**

Create `pii-washer-ui/src/components/layout/NoSessionAlert.tsx`:

```tsx
import { Button } from '@/components/ui/button';
import { useSessionStore } from '@/store/session-store';

export function NoSessionAlert() {
  const setActiveTab = useSessionStore((s) => s.setActiveTab);

  return (
    <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
      <p className="text-lg font-medium">No document loaded</p>
      <p className="text-sm">Go to the Input tab to get started.</p>
      <Button variant="outline" size="sm" className="mt-2" onClick={() => setActiveTab('input')}>
        Go to Input
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Update `ReviewTab.tsx`**

In `pii-washer-ui/src/components/tabs/ReviewTab.tsx`, add the import near the top with the other component imports:

```tsx
import { NoSessionAlert } from '@/components/layout/NoSessionAlert';
```

Find the existing "No document loaded" block (around lines 26-33) and replace the whole JSX fragment with:

```tsx
  if (!activeSessionId) {
    return <NoSessionAlert />;
  }
```

If `setActiveTab` was imported only for this panel and is not used elsewhere in the component, remove it from the imports / destructure.

Run `npm --prefix pii-washer-ui run lint` after the edit to catch any now-unused imports; `eslint-plugin-react-refresh` will flag them.

- [ ] **Step 3: Update `ResponseTab.tsx`**

Same pattern — add the import, replace the block at lines 49-59:

```tsx
  if (!activeSessionId) {
    return <NoSessionAlert />;
  }
```

- [ ] **Step 4: Update `ResultsTab.tsx`**

Same pattern — add the import, replace the block at lines 15-23.

- [ ] **Step 5: Run frontend checks**

Run: `npm --prefix pii-washer-ui run build && npm --prefix pii-washer-ui run lint && npm --prefix pii-washer-ui run test`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add pii-washer-ui/src/components/layout/NoSessionAlert.tsx pii-washer-ui/src/components/tabs/ReviewTab.tsx pii-washer-ui/src/components/tabs/ResponseTab.tsx pii-washer-ui/src/components/tabs/ResultsTab.tsx
git commit -m "refactor(ui): extract NoSessionAlert, dedupe across 3 tabs"
```

---

## Task 6: Final verification + push

- [ ] **Step 1: Full backend test run**

Run: `.venv/Scripts/python.exe -m pytest -q -m "not integration"`
Expected: all existing tests pass + new `test_api_exceptions.py` tests pass.

- [ ] **Step 2: Full frontend build + lint + test**

Run: `npm --prefix pii-washer-ui run build && npm --prefix pii-washer-ui run lint && npm --prefix pii-washer-ui run test`
Expected: all green + new ResponseTab.test passes.

- [ ] **Step 3: Review commit history**

Run: `git log --oneline origin/main..HEAD`
Expected: 6 commits total (one per task + plan doc if added separately).

- [ ] **Step 4: Review net diff**

Run: `git diff origin/main..HEAD --stat`
Expected: changes concentrated in `pii_washer/api/`, `pii_washer/session_manager.py`, `pii_washer/document_loader.py`, `pii-washer-ui/src/`, and the plan doc. No surprise files.

- [ ] **Step 5: Rewrite commit authorship to use GitHub noreply email, then push**

GitHub's email-privacy setting rejects pushes with `tron@tronlabs.net`. Rewrite the milestone commits to use the noreply address (this is the same pattern used for milestone 1):

```bash
GIT_COMMITTER_NAME="tronbonjovi" \
GIT_COMMITTER_EMAIL="165356936+tronbonjovi@users.noreply.github.com" \
git rebase origin/main --exec 'git commit --amend --no-edit --author="tronbonjovi <165356936+tronbonjovi@users.noreply.github.com>"'
```

Then:

```bash
git push origin main
```

CI will run on push. If the Linux smoketest (added in milestone 1) passes and all unit tests pass, milestone 2 is green.

---

## Self-review checklist

- [x] **Spec coverage:** All five items from the milestone scope have a task. Error classification = Task 1. MAX_FILE_SIZE layering = Task 2. ResponseTab bug = Task 3. useResetSession = Task 4. NoSessionAlert = Task 5.
- [x] **No placeholders:** Every step contains concrete code, paths, and commands. No TBD, no "similar to Task N."
- [x] **Type consistency:** `APIError` base + 4 subclasses referenced by exact name in Task 1 steps 1, 2, 4, 6. `MAX_FILE_SIZE` referenced by same name across config.py, document_loader.py, router.py in Task 2. `NoSessionAlert` referenced by same name in creation and three usage edits in Task 5.
- [x] **TDD:** Tasks 1 and 3 both write a failing test before implementation. Tasks 2, 4, 5 are refactors verified by existing tests (no new behavior to guard beyond what's already covered).
- [x] **Risk flags:** Task 1's raise-site migration is the riskiest step — it touches many lines in `session_manager.py`. Mitigation: the APIError subclasses still extend ValueError, so existing `except ValueError` handlers continue to catch them; and the `classify_value_error` fallback remains in place for any site accidentally missed.
