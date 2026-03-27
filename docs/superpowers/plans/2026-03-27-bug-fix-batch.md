# Bug Fix Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 non-session bugs found during code audit — 3 backend (Python), 3 frontend (TypeScript)

**Architecture:** Two parallel workstreams. Backend agent handles Tasks 1-2 (router.py fixes + detection engine perf). Frontend agent handles Tasks 3-5 (React component fixes). Task 6 is full verification after both complete.

**Tech Stack:** Python 3.13 / FastAPI / pytest (backend), React 19 / TypeScript / Vite (frontend)

---

## Task 1: Fix upload metadata + file size limit (Backend Bugs #1 and #5)

**Files:**
- Modify: `pii_washer/session_manager.py:63-68` — add `load_uploaded_content` method
- Modify: `pii_washer/api/router.py:102-148` — fix upload endpoint
- Modify: `pii_washer/api/config.py:4-5` — remove `MAX_UPLOAD_SIZE_BYTES`
- Modify: `pii_washer/api/router.py:6` — update import
- Test: `pii_washer/tests/test_api.py` — add upload metadata persistence test, update size limit test
- Test: `pii_washer/tests/test_session_manager.py` — add `load_uploaded_content` test

- [ ] **Step 1: Write failing test — upload metadata persists across reads**

Add to `pii_washer/tests/test_api.py` in the `TestFileUpload` class:

```python
def test_upload_metadata_persists_on_subsequent_reads(self, client):
    """Bug #1: source_format and source_filename must survive past the initial response."""
    content = b"Hello, my name is John Smith."
    r = client.post(
        "/api/v1/sessions/upload",
        files={"file": ("report.txt", io.BytesIO(content), "text/plain")},
    )
    assert r.status_code == 201
    session_id = r.json()["session_id"]

    # Read the session back — this is where the bug manifests
    r2 = client.get(f"/api/v1/sessions/{session_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["source_format"] == ".txt", f"Expected '.txt', got '{body['source_format']}'"
    assert body["source_filename"] == "report.txt", f"Expected 'report.txt', got '{body['source_filename']}'"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_api.py::TestFileUpload::test_upload_metadata_persists_on_subsequent_reads -v`
Expected: FAIL — `AssertionError: Expected '.txt', got 'paste'`

- [ ] **Step 3: Write failing test — upload size limit is 1MB (aligned with DocumentLoader)**

Update the existing test in `TestFileUpload`:

```python
def test_upload_exceeding_size_limit_returns_413(self, client):
    # 1MB + 1 byte — aligned with DocumentLoader.MAX_FILE_SIZE
    large_content = b"A" * (1_048_576 + 1)
    r = client.post(
        "/api/v1/sessions/upload",
        files={"file": ("big.txt", io.BytesIO(large_content), "text/plain")},
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_api.py::TestFileUpload::test_upload_exceeding_size_limit_returns_413 -v`
Expected: FAIL — the old test used 10MB+1, new test uses 1MB+1 which should pass the old 10MB check

- [ ] **Step 5: Write failing test — SessionManager.load_uploaded_content**

Add to `pii_washer/tests/test_session_manager.py`:

```python
class TestLoadUploadedContent:
    def test_load_uploaded_content_preserves_format_and_filename(self, manager):
        session_id = manager.load_uploaded_content("Hello world", ".txt", "report.txt")
        session = manager.get_session(session_id)
        assert session["source_format"] == ".txt"
        assert session["source_filename"] == "report.txt"
        assert session["original_text"] == "Hello world"
        assert session["status"] == "user_input"

    def test_load_uploaded_content_md_format(self, manager):
        session_id = manager.load_uploaded_content("# Title\nBody", ".md", "notes.md")
        session = manager.get_session(session_id)
        assert session["source_format"] == ".md"
        assert session["source_filename"] == "notes.md"
```

Note: The `manager` fixture is defined in `test_session_manager.py` and returns `SessionManager(detection_engine=MockDetectionEngine())`.

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_session_manager.py::TestLoadUploadedContent -v`
Expected: FAIL — `AttributeError: 'SessionManager' object has no attribute 'load_uploaded_content'`

- [ ] **Step 7: Implement SessionManager.load_uploaded_content**

Add method to `pii_washer/session_manager.py` after the existing `load_file` method (after line 75):

```python
def load_uploaded_content(self, text, source_format, filename):
    """Create a session from uploaded file content with correct metadata."""
    normalized = self.document_loader.load_text(text)
    session_id = self.store.create_session(
        normalized["text"], source_format, filename
    )
    return session_id
```

- [ ] **Step 8: Fix the upload endpoint in router.py**

In `pii_washer/api/config.py`, remove the `MAX_UPLOAD_SIZE_MB` and `MAX_UPLOAD_SIZE_BYTES` lines (lines 4-5).

In `pii_washer/api/router.py`, update the import on line 6:

```python
from .config import ALLOWED_EXTENSIONS, APP_VERSION
```

Replace the upload endpoint body (lines 115-148) with:

```python
    # Read content with streaming size check (1MB limit, aligned with DocumentLoader)
    from pii_washer.document_loader import DocumentLoader
    max_size = DocumentLoader.MAX_FILE_SIZE
    chunks = []
    total = 0
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            return JSONResponse(
                status_code=413,
                content=_error_body(
                    "FILE_TOO_LARGE",
                    f"File exceeds the {max_size // (1024 * 1024)} MB limit",
                ),
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    # Decode in memory — never write PII to disk
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "DECODE_ERROR",
                "File could not be decoded as UTF-8 text",
            ),
        )

    try:
        sm = _sm(request)
        session_id = sm.load_uploaded_content(text, suffix, file.filename)
        session = sm.get_session(session_id)
        return _to_session_created(session)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)
```

- [ ] **Step 9: Run all three tests to verify they pass**

Run: `pytest pii_washer/tests/test_api.py::TestFileUpload -v pii_washer/tests/test_session_manager.py::TestLoadUploadedContent -v`
Expected: ALL PASS

- [ ] **Step 10: Run full backend test suite for regressions**

Run: `pytest`
Expected: All 382+ tests pass

- [ ] **Step 11: Commit**

```bash
git add pii_washer/session_manager.py pii_washer/api/router.py pii_washer/api/config.py pii_washer/tests/test_api.py pii_washer/tests/test_session_manager.py
git commit -m "fix: persist upload metadata and align file size limit to 1MB"
```

---

## Task 2: Pre-compile city lookup regex (Backend Bug #7)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py:514-515` — compile regex at init
- Modify: `pii_washer/pii_detection_engine.py:666-669` — use compiled regex
- Test: `pii_washer/tests/test_pii_detection_engine.py` — add city regex test

- [ ] **Step 1: Write failing test — city lookup still works with compiled regex**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
def test_zip_with_city_context_detected(engine):
    """Bug #7: city lookup should work (we're changing its internals to a compiled regex)."""
    text = "I live in Chicago, IL 60601."
    results = engine.detect(text)
    zips = [r for r in results if r["category"] == "ADDRESS" and "60601" in r["original_value"]]
    # The ZIP should be detected because "Chicago" provides city context
    assert len(zips) >= 1, f"Expected ZIP 60601 to be detected with Chicago context, got: {[r['original_value'] for r in results]}"
```

- [ ] **Step 2: Run test to verify it passes (baseline — confirms detection works before refactor)**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::test_zip_with_city_context_detected -v`
Expected: PASS (this is a baseline test — if it fails, the city list doesn't include Chicago or the detection logic differs; adjust accordingly)

- [ ] **Step 3: Implement — pre-compile city regex at init time**

In `pii_washer/pii_detection_engine.py`, replace the city loading block (around line 513-515):

```python
        # Task 12: load city list for ZIP context — pre-compile as single alternation
        cities_path = DATA_DIR / "us_cities_top200.json"
        with open(cities_path, "r", encoding="utf-8") as f:
            cities = json.load(f)
        self._us_cities_pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(c.lower()) for c in cities) + r")\b"
        )
```

Replace the city lookup loop (lines 666-669):

```python
        # Task 12: check for known city names (single pre-compiled regex)
        if self._us_cities_pattern.search(context_lower):
            return True
```

- [ ] **Step 4: Run the test to verify it still passes**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::test_zip_with_city_context_detected -v`
Expected: PASS

- [ ] **Step 5: Run full backend test suite for regressions**

Run: `pytest`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "perf: pre-compile city lookup into single regex pattern"
```

---

## Task 3: Fix setState during render in ResponseTab (Frontend Bug #3)

**Files:**
- Modify: `pii-washer-ui/src/components/tabs/ResponseTab.tsx:1,29-41` — move to useEffect

- [ ] **Step 1: Fix — move snapshot sync into useEffect**

In `pii-washer-ui/src/components/tabs/ResponseTab.tsx`, add `useEffect` to the import on line 1:

```tsx
import { useState, useEffect } from 'react';
```

Replace lines 29-41 (the `snapshotKey` calculation and direct setState block):

```tsx
  const snapshotKey = session
    ? `${session.session_id}:${session.status === 'awaiting_response' && !!session.response_text ? 'awaiting-response' : 'loaded'}`
    : activeSessionId
      ? `loading:${activeSessionId}`
      : null;

  useEffect(() => {
    if (sessionSnapshot === snapshotKey) return;
    setSessionSnapshot(snapshotKey);
    setResponseText(
      session?.status === 'awaiting_response' && session.response_text
        ? session.response_text
        : ''
    );
  }, [snapshotKey]); // eslint-disable-line react-hooks/exhaustive-deps
```

- [ ] **Step 2: Verify frontend builds clean**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Verify lint passes**

Run: `cd pii-washer-ui && npm run lint`
Expected: No new errors

- [ ] **Step 4: Commit**

```bash
git add pii-washer-ui/src/components/tabs/ResponseTab.tsx
git commit -m "fix: move ResponseTab snapshot sync to useEffect to prevent render-loop risk"
```

---

## Task 4: Fix blob URL revoked before download starts (Frontend Bug #8)

**Files:**
- Modify: `pii-washer-ui/src/components/session/SessionActions.tsx:127` — delay revocation

- [ ] **Step 1: Fix — delay URL.revokeObjectURL**

In `pii-washer-ui/src/components/session/SessionActions.tsx`, replace line 127:

```tsx
  URL.revokeObjectURL(url);
```

with:

```tsx
  setTimeout(() => URL.revokeObjectURL(url), 100);
```

- [ ] **Step 2: Verify frontend builds clean**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add pii-washer-ui/src/components/session/SessionActions.tsx
git commit -m "fix: delay blob URL revocation so browser can start download"
```

---

## Task 5: Fix "Confirm All" button ignoring edit lock (Frontend Bug #9)

**Files:**
- Modify: `pii-washer-ui/src/components/review/BulkActions.tsx:55` — add can_edit_detections check

- [ ] **Step 1: Fix — add can_edit_detections to disabled prop**

In `pii-washer-ui/src/components/review/BulkActions.tsx`, replace line 55:

```tsx
          disabled={sessionStatus.pending_count === 0 || confirmAll.isPending}
```

with:

```tsx
          disabled={sessionStatus.pending_count === 0 || !sessionStatus.can_edit_detections || confirmAll.isPending}
```

- [ ] **Step 2: Verify frontend builds clean**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add pii-washer-ui/src/components/review/BulkActions.tsx
git commit -m "fix: disable Confirm All button when detections are not editable"
```

---

## Task 6: Full verification

- [ ] **Step 1: Run full backend test suite**

Run: `pytest`
Expected: All tests pass (382+)

- [ ] **Step 2: Run frontend build**

Run: `cd pii-washer-ui && npm run build`
Expected: Clean build

- [ ] **Step 3: Run frontend lint**

Run: `cd pii-washer-ui && npm run lint`
Expected: No errors

- [ ] **Step 4: Review all changes**

Run: `git diff main --stat`
Verify only the expected files were modified.
