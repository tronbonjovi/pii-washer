# Codex Review Remediation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 8 actionable findings from the Codex adversarial review — API security hardening, detection coverage, and a UI bug.

**Architecture:** Surgical fixes to existing files. No new components or architectural changes. Milestone 1 (Tasks 1-6) hardens the API layer. Milestone 2 (Tasks 7-8) fixes detection coverage and a UI error message.

**Tech Stack:** Python/FastAPI/Pydantic (backend), React/TypeScript (frontend), pytest (tests)

**Spec:** `docs/superpowers/specs/2026-04-02-codex-review-remediation-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `pii_washer/api/models.py` | Remove `original_text` from `SessionCreatedResponse`, add `SessionDetailResponse` |
| Modify | `pii_washer/api/router.py` | Update `_to_session_created`, add `_to_session_detail`, type `get_session` endpoint |
| Modify | `pii_washer/api/errors.py` | Sanitize `server_error_response` message |
| Modify | `pii_washer/api/main.py` | Tighten CORS methods/headers |
| Modify | `pii_washer/api/update_checker.py` | Fix httpx client leak |
| Modify | `pii_washer/session_manager.py` | Add placeholder content validation |
| Modify | `pii_washer/name_recognizer.py` | Add all-caps support to `DictionaryNameRecognizer` and `TitleNameRecognizer` |
| Modify | `pii_washer/tests/test_api.py` | Update creation assertions, add error sanitization test, add placeholder validation test |
| Modify | `pii_washer/tests/test_session_manager.py` | Add placeholder validation tests |
| Modify | `pii_washer/tests/test_name_recognizer.py` | Add all-caps detection tests |
| Modify | `pii-washer-ui/src/types/api.ts` | Remove `original_text` from `SessionCreatedResponse` |
| Modify | `pii-washer-ui/src/components/tabs/InputTab.tsx` | Fix "10 MB" → "1 MB" |

---

## Milestone 1: API Hardening

### Task 1: Remove `original_text` from session creation response

**Files:**
- Modify: `pii_washer/api/models.py:45-50`
- Modify: `pii_washer/api/router.py:49-56`
- Modify: `pii_washer/tests/test_api.py:149`
- Modify: `pii-washer-ui/src/types/api.ts:79-85`

- [ ] **Step 1: Write the failing test**

In `pii_washer/tests/test_api.py`, add a new test to `TestSessionCRUD`:

```python
def test_create_session_does_not_return_original_text(self, client):
    r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
    assert r.status_code == 201
    assert "original_text" not in r.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_api.py::TestSessionCRUD::test_create_session_does_not_return_original_text -v`
Expected: FAIL — `original_text` is currently in the response

- [ ] **Step 3: Remove `original_text` from backend**

In `pii_washer/api/models.py`, remove the `original_text` field from `SessionCreatedResponse`:

```python
class SessionCreatedResponse(BaseModel):
    session_id: str
    status: str
    source_format: str
    source_filename: str | None
```

In `pii_washer/api/router.py`, remove `original_text` from `_to_session_created`:

```python
def _to_session_created(session: dict) -> SessionCreatedResponse:
    return SessionCreatedResponse(
        session_id=session["session_id"],
        status=session["status"],
        source_format=session["source_format"],
        source_filename=session["source_filename"],
    )
```

- [ ] **Step 4: Update the existing test that asserts `original_text`**

In `pii_washer/tests/test_api.py`, `TestSessionCRUD::test_create_from_text_returns_201`, remove line 149:

```python
# REMOVE this line:
# assert body["original_text"] == SAMPLE_TEXT
```

The test should now assert only the fields that remain:

```python
def test_create_from_text_returns_201(self, client):
    r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
    assert r.status_code == 201
    body = r.json()
    assert "session_id" in body
    assert body["status"] == "user_input"
    assert body["source_format"] == "paste"
    assert body["source_filename"] is None
```

- [ ] **Step 5: Update the frontend type**

In `pii-washer-ui/src/types/api.ts`, remove `original_text` from `SessionCreatedResponse`:

```typescript
export interface SessionCreatedResponse {
  session_id: string;
  status: SessionStatus;
  source_format: string;
  source_filename: string | null;
}
```

- [ ] **Step 6: Run all tests to verify**

Run: `pytest pii_washer/tests/test_api.py -v`
Expected: ALL PASS

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds with no type errors

- [ ] **Step 7: Commit**

```bash
git add pii_washer/api/models.py pii_washer/api/router.py pii_washer/tests/test_api.py pii-washer-ui/src/types/api.ts
git commit -m "fix: remove original_text from session creation response

PII-laden text no longer round-trips in the creation response.
The frontend only uses session_id from this endpoint."
```

---

### Task 2: Add typed `SessionDetailResponse` for `GET /sessions/{id}`

**Files:**
- Modify: `pii_washer/api/models.py`
- Modify: `pii_washer/api/router.py:182-191`

- [ ] **Step 1: Write the failing test**

In `pii_washer/tests/test_api.py`, add a test to `TestSessionCRUD` that verifies the response matches a known schema:

```python
def test_get_session_returns_typed_response(self, client):
    """GET /sessions/{id} must return exactly the expected fields."""
    r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
    session_id = r.json()["session_id"]
    r2 = client.get(f"/api/v1/sessions/{session_id}")
    assert r2.status_code == 200
    body = r2.json()
    expected_keys = {
        "session_id", "status", "created_at", "updated_at",
        "source_format", "source_filename", "original_text",
        "pii_detections", "depersonalized_text", "response_text",
        "repersonalized_text", "unmatched_placeholders",
    }
    assert set(body.keys()) == expected_keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_api.py::TestSessionCRUD::test_get_session_returns_typed_response -v`
Expected: FAIL — raw dict may have extra or different keys than expected

- [ ] **Step 3: Add `SessionDetailResponse` model**

In `pii_washer/api/models.py`, add after `SessionCreatedResponse`:

```python
class SessionDetailResponse(BaseModel):
    session_id: str
    status: str
    created_at: str
    updated_at: str
    source_format: str
    source_filename: str | None
    original_text: str
    pii_detections: list[Detection]
    depersonalized_text: str | None
    response_text: str | None
    repersonalized_text: str | None
    unmatched_placeholders: list[str]
```

- [ ] **Step 4: Wire up the typed response in the router**

In `pii_washer/api/router.py`, add the import of `SessionDetailResponse` to the import block:

```python
from .models import (
    ...
    SessionCreatedResponse,
    SessionDetailResponse,
    ...
)
```

Add a helper function after `_to_session_created`:

```python
def _to_session_detail(session: dict) -> SessionDetailResponse:
    return SessionDetailResponse(
        session_id=session["session_id"],
        status=session["status"],
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        source_format=session["source_format"],
        source_filename=session["source_filename"],
        original_text=session["original_text"],
        pii_detections=[_to_detection(d) for d in session.get("pii_detections", [])],
        depersonalized_text=session.get("depersonalized_text"),
        response_text=session.get("response_text"),
        repersonalized_text=session.get("repersonalized_text"),
        unmatched_placeholders=session.get("unmatched_placeholders", []),
    )
```

Update the `get_session` endpoint:

```python
@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str, request: Request):
    sm = _sm(request)
    try:
        session = sm.get_session(session_id)
        return _to_session_detail(session)
    except KeyError as exc:
        return key_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)
```

- [ ] **Step 5: Run tests to verify**

Run: `pytest pii_washer/tests/test_api.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add pii_washer/api/models.py pii_washer/api/router.py pii_washer/tests/test_api.py
git commit -m "fix: add typed SessionDetailResponse for GET /sessions/{id}

Replaces raw JSONResponse(content=session) with a Pydantic model.
Prevents accidental field leaks and provides API documentation."
```

---

### Task 3: Sanitize server error response

**Files:**
- Modify: `pii_washer/api/errors.py:48-53`
- Modify: `pii_washer/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

In `pii_washer/tests/test_api.py`, add a test to `TestErrorHandling`:

```python
def test_server_error_does_not_leak_exception_details(self, client):
    """500 responses must not expose internal exception class or message."""
    r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
    session_id = r.json()["session_id"]
    # Force a 500 by directly breaking state via the session manager
    sm = client.app.state.session_manager
    sm.store._sessions[session_id]["status"] = "nonexistent_status"
    # Try an operation that will fail with an unexpected error
    from unittest.mock import patch
    with patch.object(sm, "get_session", side_effect=TypeError("internal details")):
        r = client.get(f"/api/v1/sessions/{session_id}")
    assert r.status_code == 500
    msg = r.json()["error"]["message"]
    assert "TypeError" not in msg
    assert "internal details" not in msg
    assert msg == "An unexpected error occurred"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_api.py::TestErrorHandling::test_server_error_does_not_leak_exception_details -v`
Expected: FAIL — current message contains `TypeError: internal details`

- [ ] **Step 3: Sanitize the error message**

In `pii_washer/api/errors.py`, change `server_error_response`:

```python
def server_error_response(exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_body("SERVER_ERROR", "An unexpected error occurred"),
    )
```

- [ ] **Step 4: Run tests to verify**

Run: `pytest pii_washer/tests/test_api.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add pii_washer/api/errors.py pii_washer/tests/test_api.py
git commit -m "fix: sanitize server error response to hide internal details

500 responses no longer expose exception class names or messages.
Full details remain available in the log file for debugging."
```

---

### Task 4: Tighten CORS configuration

**Files:**
- Modify: `pii_washer/api/main.py:61-66`

- [ ] **Step 1: Tighten CORS methods and headers**

In `pii_washer/api/main.py`, change the CORS middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)
```

- [ ] **Step 2: Run tests to verify nothing breaks**

Run: `pytest pii_washer/tests/test_api.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add pii_washer/api/main.py
git commit -m "fix: tighten CORS to only allow used methods and headers"
```

---

### Task 5: Fix httpx client leak in update checker

**Files:**
- Modify: `pii_washer/api/update_checker.py:31-37`

- [ ] **Step 1: Wrap httpx client in async context manager**

In `pii_washer/api/update_checker.py`, change the `try` block:

```python
try:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10.0,
        )

        # Support both real httpx (sync json) and test mocks (async json)
        json_result = resp.json()
        data = await json_result if inspect.isawaitable(json_result) else json_result
```

The rest of the function (tag parsing, version comparison, return statements, except block) remains unchanged.

- [ ] **Step 2: Run tests to verify**

Run: `pytest pii_washer/tests/test_update_checker.py -v`
Expected: ALL PASS (tests already mock `__aenter__`/`__aexit__`)

- [ ] **Step 3: Commit**

```bash
git add pii_washer/api/update_checker.py
git commit -m "fix: close httpx client properly using async context manager"
```

---

### Task 6: Validate custom placeholder content

**Files:**
- Modify: `pii_washer/session_manager.py:156-164`
- Modify: `pii_washer/tests/test_session_manager.py`
- Modify: `pii_washer/tests/test_api.py`

- [ ] **Step 1: Write failing tests for invalid placeholders**

In `pii_washer/tests/test_session_manager.py`, add to `TestEditPlaceholder`:

```python
def test_edit_placeholder_special_chars_raises(self, manager):
    """Placeholders with special characters must be rejected."""
    sid = manager.load_text(SAMPLE_TEXT)
    detections = manager.analyze(sid)
    det_id = detections[0]["id"]
    with pytest.raises(ValueError, match="can only contain"):
        manager.edit_detection_placeholder(sid, det_id, "<script>alert(1)</script>")

def test_edit_placeholder_too_long_raises(self, manager):
    """Placeholders longer than 50 characters must be rejected."""
    sid = manager.load_text(SAMPLE_TEXT)
    detections = manager.analyze(sid)
    det_id = detections[0]["id"]
    with pytest.raises(ValueError, match="cannot exceed 50"):
        manager.edit_detection_placeholder(sid, det_id, "[" + "A" * 60 + "]")

def test_edit_placeholder_brackets_and_underscores_allowed(self, manager):
    """Placeholders with brackets, underscores, hyphens, and spaces are valid."""
    sid = manager.load_text(SAMPLE_TEXT)
    detections = manager.analyze(sid)
    det_id = detections[0]["id"]
    result = manager.edit_detection_placeholder(sid, det_id, "[My Client-Name 1]")
    assert result["placeholder"] == "[My Client-Name 1]"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_session_manager.py::TestEditPlaceholder::test_edit_placeholder_special_chars_raises -v`
Expected: FAIL — no validation exists yet

- [ ] **Step 3: Add validation to `edit_detection_placeholder`**

In `pii_washer/session_manager.py`, add validation after the empty check at line 164. Add `import re` at the top if not already present (it is — line 8):

```python
def edit_detection_placeholder(self, session_id, detection_id, new_placeholder):
    session = self.store.get_session(session_id)
    sess_status = session["status"]
    if sess_status != "analyzed":
        raise ValueError(
            f"Cannot update detections: session status is '{sess_status}', expected 'analyzed'"
        )
    if not new_placeholder:
        raise ValueError("Placeholder cannot be empty")
    if len(new_placeholder) > 50:
        raise ValueError("Placeholder cannot exceed 50 characters")
    if not re.match(r'^[A-Za-z0-9_\-\[\] ]+$', new_placeholder):
        raise ValueError(
            "Placeholder can only contain letters, numbers, underscores, "
            "hyphens, spaces, and brackets"
        )
    # ... rest of method unchanged
```

- [ ] **Step 4: Run tests to verify**

Run: `pytest pii_washer/tests/test_session_manager.py::TestEditPlaceholder -v`
Expected: ALL PASS

Run: `pytest pii_washer/tests/test_api.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add pii_washer/session_manager.py pii_washer/tests/test_session_manager.py
git commit -m "fix: validate custom placeholder content

Rejects special characters and placeholders over 50 chars.
Allows letters, numbers, underscores, hyphens, spaces, brackets."
```

---

## Milestone 2: Detection Fix + Bug Fix

### Task 7: Add all-caps name detection

**Files:**
- Modify: `pii_washer/name_recognizer.py:96` (DictionaryNameRecognizer)
- Modify: `pii_washer/name_recognizer.py:30-33` (TitleNameRecognizer)
- Modify: `pii_washer/tests/test_name_recognizer.py`

The `CapitalizedPairRecognizer` is intentionally NOT updated — without a dictionary backing, all-caps support would produce too many false positives (e.g., "QUICK FOX").

- [ ] **Step 1: Write failing tests for all-caps names**

In `pii_washer/tests/test_name_recognizer.py`, add to `TestDictionaryNameRecognizer`:

```python
def test_all_caps_full_name(self, dict_recognizer):
    """ALL CAPS names like 'JOHN SMITH' must be detected."""
    text = "The patient JOHN SMITH was admitted."
    results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
    assert any("JOHN SMITH" in text[r.start:r.end] for r in results)

def test_all_caps_three_word_name(self, dict_recognizer):
    """Three-word ALL CAPS names must be detected."""
    text = "Signed by MARY JANE WATSON on this date."
    results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
    assert any("MARY" in text[r.start:r.end] and "WATSON" in text[r.start:r.end] for r in results)

def test_all_caps_first_name_no_surname_still_skipped(self, dict_recognizer):
    """A lone ALL CAPS first name without a capitalized surname should not match."""
    text = "JAMES went to the store."
    results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
    assert len(results) == 0
```

Add to `TestTitleNameRecognizer`:

```python
def test_title_with_all_caps_name(self, analyzer):
    """Titles followed by ALL CAPS names must be detected."""
    text = "Dr. JANE DOE will see you now."
    results = analyzer.analyze(text, language="en", entities=["PERSON"])
    persons = [r for r in results if r.entity_type == "PERSON"]
    texts = [text[r.start:r.end] for r in persons]
    assert any("JANE" in t and "DOE" in t for t in texts)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_name_recognizer.py::TestDictionaryNameRecognizer::test_all_caps_full_name -v`
Expected: FAIL — all-caps surnames rejected by `next_word[1:].islower()` check

Run: `pytest pii_washer/tests/test_name_recognizer.py::TestTitleNameRecognizer::test_title_with_all_caps_name -v`
Expected: FAIL — regex `[A-Z][a-z]+` doesn't match all-caps words

- [ ] **Step 3: Fix `DictionaryNameRecognizer` to accept all-caps surnames**

In `pii_washer/name_recognizer.py`, change line 96 in the `analyze` method of `DictionaryNameRecognizer`:

Replace:
```python
if not next_word[0].isupper() or not next_word[1:].islower():
    break
```

With:
```python
if not next_word[0].isupper():
    break
if not (next_word[1:].islower() or next_word.isupper()):
    break
```

This accepts both title-case (`Smith`) and all-caps (`SMITH`) but still rejects mixed-case like `sMITH`.

- [ ] **Step 4: Fix `TitleNameRecognizer` to accept all-caps names after titles**

In `pii_washer/name_recognizer.py`, change the `pattern_text` in `TitleNameRecognizer.__init__`:

Replace:
```python
pattern_text = (
    r"\b(?:" + title_alternation + r")\.?\s+"
    r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b"
)
```

With:
```python
pattern_text = (
    r"\b(?:" + title_alternation + r")\.?\s+"
    r"[A-Z](?:[a-z]+|[A-Z]+)(?:\s+[A-Z](?:[a-z]+|[A-Z]+)){0,2}\b"
)
```

This matches each name word as either title-case (`[A-Z][a-z]+`) or all-caps (`[A-Z][A-Z]+`).

- [ ] **Step 5: Run all name recognizer tests**

Run: `pytest pii_washer/tests/test_name_recognizer.py -v`
Expected: ALL PASS (new tests pass, existing tests still pass)

- [ ] **Step 6: Run full test suite to check for regressions**

Run: `pytest pii_washer/tests/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add pii_washer/name_recognizer.py pii_washer/tests/test_name_recognizer.py
git commit -m "fix: detect ALL CAPS names in DictionaryNameRecognizer and TitleNameRecognizer

Legal documents, medical forms, and data entry systems commonly use
ALL CAPS for names. Previously only title-case was detected."
```

---

### Task 8: Fix "10 MB" error message

**Files:**
- Modify: `pii-washer-ui/src/components/tabs/InputTab.tsx:18`

- [ ] **Step 1: Fix the error message**

In `pii-washer-ui/src/components/tabs/InputTab.tsx`, change line 18:

Replace:
```typescript
return 'The file is too large. Maximum size is 10 MB.';
```

With:
```typescript
return 'The file is too large. Maximum size is 1 MB.';
```

- [ ] **Step 2: Verify the frontend builds**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add pii-washer-ui/src/components/tabs/InputTab.tsx
git commit -m "fix: correct file size error message from 10 MB to 1 MB"
```

---

## Final Verification

After all tasks are complete:

- [ ] **Run the full backend test suite**

Run: `pytest pii_washer/tests/ -v`
Expected: ALL PASS

- [ ] **Run the frontend build check**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds with no errors
