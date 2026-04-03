# Codex Review Remediation — Design Spec

**Date:** 2026-04-02
**Context:** Codex adversarial review of the full PII Washer codebase surfaced 22 findings. This spec covers the 8 findings triaged as "fix now" — real bugs, security gaps, and detection quality issues. Remaining findings are deferred to existing roadmap items or skipped as not applicable to a local single-user tool.

## Scope

Two milestones: API hardening (6 fixes) and detection/bug fix (2 fixes). No user-facing behavior changes except corrected error messaging and improved PII detection coverage.

### Out of scope

- `secure_clear` memory limitations — deferred to roadmap near-term #4 (Security assessment)
- Detection tuning (false positives, international formats, dates) — deferred to medium-term (Detection improvements v2)
- Frontend tests, error boundaries, state persistence — deferred to future sessions
- Internal data representation (dicts vs typed objects) — code quality preference, not a bug
- Rate limiting, session ID entropy, race conditions — not applicable to local single-user tool

---

## Milestone 1: API Hardening

### 1. Remove `original_text` from `SessionCreatedResponse`

**File:** `pii_washer/api/models.py:50`

The `SessionCreatedResponse` model includes `original_text`, which means the full PII-laden text round-trips over HTTP on session creation. It ends up in the browser's network response cache, React Query cache, and DevTools history.

**Change:** Remove the `original_text` field from `SessionCreatedResponse`. The frontend fetches session data separately for the Review tab — it does not need the text eagerly on creation.

**Verify:** Confirm the frontend `useCreateSession` mutation does not depend on `original_text` from the creation response.

### 2. Type the `GET /sessions/{id}` response

**File:** `pii_washer/api/router.py:182-191`

The `get_session` endpoint returns `JSONResponse(content=session)` where `session` is a raw dict from the store. This bypasses Pydantic validation and could leak unexpected fields. Every other endpoint uses typed response models.

**Change:**
- Create a `SessionDetailResponse` Pydantic model that selectively exposes fields needed by the frontend
- Exclude `original_text` from this model — serve it only through the workflow endpoints that need it (depersonalize, etc.)
- Replace the raw `JSONResponse` with the typed model

### 3. Sanitize `server_error_response`

**File:** `pii_washer/api/errors.py:52`

The error response includes `f"An unexpected error occurred: {type(exc).__name__}: {exc}"`, which leaks internal exception class names and messages to the client. Could expose file paths, library internals, or internal state.

**Change:** Replace with a generic message: `"An unexpected error occurred"`. The `logger.exception()` on the preceding line already captures full details for debugging.

### 4. Tighten CORS methods and headers

**File:** `pii_washer/api/main.py:64-65`

CORS middleware uses `allow_methods=["*"]` and `allow_headers=["*"]`. Only GET, POST, PATCH, and OPTIONS with Content-Type are actually used.

**Change:**
- `allow_methods=["GET", "POST", "PATCH", "OPTIONS"]`
- `allow_headers=["Content-Type"]`

### 5. Fix httpx client leak in update checker

**File:** `pii_washer/api/update_checker.py:32`

`httpx.AsyncClient()` is instantiated directly without a context manager. The client is never closed, leaking connections.

**Change:** Wrap in `async with httpx.AsyncClient() as client:`.

### 6. Validate custom placeholder content

**File:** `pii_washer/session_manager.py:163`

`edit_detection_placeholder` only checks if the placeholder is empty. Users can set any string, including content that could collide with document text or cause display issues.

**Change:**
- Validate format: must contain only alphanumeric characters, underscores, hyphens, and spaces (`[A-Za-z0-9_\- ]+`)
- Enforce max length of 50 characters
- Raise `ValueError` with a descriptive message on invalid input

---

## Milestone 2: Detection Fix + Bug Fix

### 7. Add all-caps name detection

**File:** `pii_washer/name_recognizer.py:81`

The `DictionaryNameRecognizer` requires `word[0].isupper()`, which matches title-case (`John`) but misses all-caps (`JOHN`). Legal documents, medical forms, and data entry systems commonly use all-caps for names. This is a real PII leakage vector.

**Change:**
- Change the check to accept both title-case and all-caps words
- The dictionary lookup already lowercases (`word.lower() not in self._first_names`), so matching logic is unaffected
- Check `CapitalizedPairRecognizer` for the same casing limitation and fix if present
- Add test cases for all-caps names (single names, full names, mixed-case documents)

### 8. Fix "10 MB" error message

**File:** `pii-washer-ui/src/components/tabs/InputTab.tsx:18`

Error message says `'The file is too large. Maximum size is 10 MB.'` but the actual limit is 1 MB (`DocumentLoader.MAX_FILE_SIZE = 1_048_576`).

**Change:** Update to `'The file is too large. Maximum size is 1 MB.'`

---

## Testing

- **Milestone 1:** Existing API tests should continue to pass. Add/update tests for:
  - `SessionCreatedResponse` no longer includes `original_text`
  - `GET /sessions/{id}` returns typed response with expected fields
  - `server_error_response` returns generic message
  - `edit_detection_placeholder` rejects invalid placeholders (special chars, too long, empty)
- **Milestone 2:**
  - Add test cases for all-caps name detection in `test_pii_detection_engine.py`
  - Verify no regression in title-case detection

## Deferred Items — Roadmap Mapping

| Codex Finding | Deferred To |
|---|---|
| `secure_clear` doesn't erase Python strings from memory | Roadmap near-term #4: Security assessment |
| International PII formats not detected | Roadmap medium-term: Detection improvements v2 |
| Date false positives at 0.2 confidence | Roadmap medium-term: Detection improvements v2 |
| `CapitalizedPairRecognizer` false positive rate | Roadmap medium-term: Detection improvements v2 |
| No frontend tests | Future session: Frontend test infrastructure |
| No integration tests with real Presidio | Future session: Test infrastructure |
| App state lost on refresh | Roadmap near-term #2: UX polish batch |
| No React error boundaries | Roadmap near-term #2: UX polish batch |
| `PLACEHOLDER_PATTERN` misses custom placeholders | Low impact edge case — revisit with detection improvements |
