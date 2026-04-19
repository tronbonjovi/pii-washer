# Housekeeping & Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the app version to a single source, delete dead code from prior iterations, and harden the release workflow against upcoming PyInstaller breakage and silent hidden-import drift.

**Architecture:** Ten small commits, each scoped to one concern. Version consolidation moves the single source of truth to `pyproject.toml` and reads it at runtime via `importlib.metadata`. Dead-code tasks delete unreferenced modules + tests. Release workflow tasks switch macOS to `--onedir` (zipped for upload), align release Python to the minimum supported version (3.11), and add a post-build smoke test on Linux to catch missing hidden imports before users do.

**Tech Stack:** Python 3.11–3.13, FastAPI, React/TS/Vite, PyInstaller, GitHub Actions.

---

## Pre-flight

Everything happens on the existing `main` branch with clean working tree. No worktree needed — changes are low-risk and reviewable commit by commit.

Before starting: verify tests pass on baseline.

- [ ] **Run baseline tests** to establish green starting point

Run: `pytest -q`
Expected: PASS (all existing tests green)

Run: `cd pii-washer-ui && npm run build && npm run lint && npm run test`
Expected: build OK, lint OK, tests pass

---

## Task 1: Version consolidation via `importlib.metadata`

**Files:**
- Modify: `pii_washer/api/config.py` (remove `APP_VERSION` constant, add `get_app_version()` function)
- Modify: `pii_washer/api/main.py:8,49,57` (import + use `get_app_version()` instead of `APP_VERSION`)
- Modify: `pii_washer/api/router.py:9,99` (import + use `get_app_version()` instead of `APP_VERSION`)
- Modify: `pii_washer/__init__.py` (remove stale `__version__`)
- Modify: `pii-washer-ui/package.json:4` (remove dummy `"version": "0.0.0"`)
- Modify: `CLAUDE.md` (update the "Version is tracked in two places" paragraph to reflect single source)
- Test: `pii_washer/tests/test_api.py` (add one assertion that confirms runtime version matches `pyproject.toml`)

Rationale: the version only ever needs to be set in one place (`pyproject.toml`). `importlib.metadata.version("pii-washer")` reads from the installed package metadata, which is populated by setuptools at install time. This is the standard Python pattern for a single source of truth.

- [ ] **Step 1: Write the failing test**

Append to `pii_washer/tests/test_api.py` (near the existing health/root tests):

```python
def test_version_endpoint_matches_package_metadata(client):
    """Version reported by the API must match the installed package metadata."""
    from importlib.metadata import version as pkg_version

    expected = pkg_version("pii-washer")

    health = client.get("/api/v1/health").json()
    assert health["version"] == expected

    root = client.get("/").json()
    assert root["version"] == expected
```

- [ ] **Step 2: Run test to verify it passes on current code (sanity)**

Run: `pytest pii_washer/tests/test_api.py::test_version_endpoint_matches_package_metadata -v`
Expected: PASS (existing hardcoded `APP_VERSION = "1.2.0"` matches `pyproject.toml` version = `"1.2.0"`)

Note: this test will still pass after we refactor — the whole point is it keeps passing while we swap the implementation underneath.

- [ ] **Step 3: Refactor `config.py` to read from package metadata**

Replace `pii_washer/api/config.py` entirely with:

```python
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version

API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
DEFAULT_PORT = 8000
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx", ".html"}
BINARY_FORMATS = {".docx", ".pdf", ".csv", ".xlsx", ".html"}
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
]


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Return the installed package version. Single source of truth: pyproject.toml."""
    try:
        return version("pii-washer")
    except PackageNotFoundError:
        return "0.0.0+unknown"
```

Note: Tauri CORS entries are left in place in this task — they're removed in Task 2 so the diff stays scoped.

- [ ] **Step 4: Update `main.py` to use `get_app_version()`**

In `pii_washer/api/main.py`:

Change line 8 from:
```python
from .config import API_PREFIX, APP_VERSION, CORS_ORIGINS
```
to:
```python
from .config import API_PREFIX, CORS_ORIGINS, get_app_version
```

Change line 49 from:
```python
logger.info("PII Washer %s started (log: %s)", APP_VERSION, _log_file)
```
to:
```python
logger.info("PII Washer %s started (log: %s)", get_app_version(), _log_file)
```

Change line 57 from:
```python
version=APP_VERSION,
```
to:
```python
version=get_app_version(),
```

- [ ] **Step 5: Update `router.py` to use `get_app_version()`**

In `pii_washer/api/router.py`:

Change line 9 from:
```python
from .config import ALLOWED_EXTENSIONS, APP_VERSION, BINARY_FORMATS
```
to:
```python
from .config import ALLOWED_EXTENSIONS, BINARY_FORMATS, get_app_version
```

Change line 99 from:
```python
version=APP_VERSION,
```
to:
```python
version=get_app_version(),
```

- [ ] **Step 6: Delete stale `__version__` from `__init__.py`**

Replace `pii_washer/__init__.py` entirely with:

```python
"""Pii Washer — Local-only PII detection and text sanitization."""
```

- [ ] **Step 7: Remove dummy version from frontend `package.json`**

In `pii-washer-ui/package.json`, delete line 4 (`"version": "0.0.0",`). The frontend is not published as a package; a version field here is misleading.

- [ ] **Step 8: Run full test suite**

Run: `pytest -q`
Expected: PASS (the version test from Step 1 still passes; nothing else regresses)

- [ ] **Step 9: Update CLAUDE.md**

Find the paragraph that starts with "**Version is tracked in two places**" under "Key Constraints" and replace it with:

```markdown
- **Version has a single source of truth: `pyproject.toml`.** The API reads it at runtime via `importlib.metadata.version("pii-washer")` (see `get_app_version()` in `pii_washer/api/config.py`). Only update `pyproject.toml` when bumping.
```

- [ ] **Step 10: Commit**

```bash
git add pii_washer/api/config.py pii_washer/api/main.py pii_washer/api/router.py pii_washer/__init__.py pii_washer/tests/test_api.py pii-washer-ui/package.json CLAUDE.md
git commit -m "refactor: consolidate version to pyproject.toml via importlib.metadata"
```

---

## Task 2: Remove Tauri CORS entries

**Files:**
- Modify: `pii_washer/api/config.py:11-13` (delete tauri origins from `CORS_ORIGINS`)

Rationale: Tauri was removed from the project. These origins serve no app and widen the CORS allowlist.

- [ ] **Step 1: Edit `config.py` to remove Tauri origins**

In `pii_washer/api/config.py`, replace the `CORS_ORIGINS` list with:

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
```

- [ ] **Step 2: Run tests**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add pii_washer/api/config.py
git commit -m "chore: remove Tauri CORS origins (Tauri was removed from project)"
```

---

## Task 3: Remove orphaned `SessionManager` methods

**Files:**
- Modify: `pii_washer/session_manager.py:328-332` (delete `get_depersonalized_text`)
- Modify: `pii_washer/session_manager.py:349-362` (delete `load_response_file`)
- Modify: `pii_washer/tests/test_session_manager.py:435-447` (delete `test_get_depersonalized_text` and `test_get_depersonalized_text_before_depersonalization`)
- Modify: `pii_washer/tests/test_session_manager.py:466-473` (delete `test_load_response_file`)

Rationale: Both methods are defined and tested but never called by any router or other component. They're leftovers from an earlier design. Remove the code + the tests that only exist to exercise them.

- [ ] **Step 1: Re-verify methods are unreferenced**

Run: `rg -n "get_depersonalized_text|load_response_file" pii_washer/`
Expected: matches only in `session_manager.py` (defs) and `tests/test_session_manager.py` (tests) — NOT in router, main, or any production caller.

If this turns up unexpected callers, stop and flag it. Otherwise proceed.

- [ ] **Step 2: Delete `get_depersonalized_text` from session_manager.py**

In `pii_washer/session_manager.py`, remove the method at lines 328-332:

```python
    def get_depersonalized_text(self, session_id):
        session = self.store.get_session(session_id)
        if session["depersonalized_text"] is None:
            raise ValueError("Session has not been depersonalized yet")
        return session["depersonalized_text"]
```

- [ ] **Step 3: Delete `load_response_file` from session_manager.py**

In `pii_washer/session_manager.py`, remove the method at lines 349-362:

```python
    def load_response_file(self, session_id, filepath):
        session = self.store.get_session(session_id)
        status = session["status"]
        if status != "depersonalized":
            raise ValueError(
                f"Cannot load response: session status is '{status}', expected 'depersonalized'"
            )

        result = self.document_loader.load_file(filepath)
        self.store.update_session(session_id, {
            "response_text": result["text"],
            "status": "awaiting_response",
        })
        return result["text"]
```

- [ ] **Step 4: Delete the three orphan tests in `test_session_manager.py`**

In `pii_washer/tests/test_session_manager.py`, delete:
- `test_get_depersonalized_text` (starts at line 435)
- `test_get_depersonalized_text_before_depersonalization` (starts at line 443)
- `test_load_response_file` (starts at line 466)

Leave every other test in the file intact.

- [ ] **Step 5: Run tests**

Run: `pytest -q`
Expected: PASS (fewer tests, none red)

- [ ] **Step 6: Commit**

```bash
git add pii_washer/session_manager.py pii_washer/tests/test_session_manager.py
git commit -m "chore: remove orphaned SessionManager methods and their tests"
```

---

## Task 4: Frontend dead-code sweep

**Files:**
- Delete: `pii-washer-ui/src/App.css`
- Modify: `pii-washer-ui/src/hooks/use-workflow.ts:10-21` (delete unused `useAnalyze` export)
- Delete: `pii-washer-ui/src/api/health.ts`

Rationale: `App.css` is Vite scaffolding never imported. `useAnalyze` is superseded by `useAnalyzeDocument` (confirmed no imports). `health.ts` exports `getHealth()` which is never imported anywhere in the UI.

- [ ] **Step 1: Re-verify each is unreferenced**

Run: `cd pii-washer-ui && rg -n "App\.css|useAnalyze[^D]|getHealth" src/`
Expected: only the definitions show up, not any imports from outside their defining files.

If any import exists, stop and flag it.

- [ ] **Step 2: Delete `App.css`**

```bash
rm pii-washer-ui/src/App.css
```

- [ ] **Step 3: Delete `useAnalyze` from `use-workflow.ts`**

In `pii-washer-ui/src/hooks/use-workflow.ts`, remove the `useAnalyze` export (lines 10-21). Also remove `analyzeSession` from the top-level import on line 3 if it's no longer used elsewhere in the file (it won't be — other hooks in this file use `depersonalizeSession`, `loadResponseText`, `repersonalizeSession`).

Final file should start with:

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  depersonalizeSession,
  loadResponseText,
  repersonalizeSession,
} from '@/api/workflow';
import type { Session } from '@/types/api';

export function useDepersonalize(sessionId: string) {
```

...and keep the three remaining hooks (`useDepersonalize`, `useLoadResponse`, `useRepersonalize`) as-is.

- [ ] **Step 4: Delete `health.ts`**

```bash
rm pii-washer-ui/src/api/health.ts
```

- [ ] **Step 5: Run frontend build, lint, and tests**

Run: `cd pii-washer-ui && npm run build`
Expected: PASS (no missing-import errors)

Run: `cd pii-washer-ui && npm run lint`
Expected: PASS

Run: `cd pii-washer-ui && npm run test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A pii-washer-ui/
git commit -m "chore: delete dead frontend code (App.css, useAnalyze hook, health.ts)"
```

---

## Task 5: `.gitignore` cleanup

**Files:**
- Modify: `.gitignore:65` (remove `pii-washer-ui/src-tauri/` entry)

Rationale: directory does not exist. The project migrated off Tauri long ago.

- [ ] **Step 1: Remove the stale entry**

In `.gitignore`, delete the line `pii-washer-ui/src-tauri/` (line 65). If there's a blank line or comment immediately above/below that becomes orphaned, tidy that too.

- [ ] **Step 2: Verify `.gitignore` still valid**

Run: `git check-ignore pii-washer-ui/src/App.tsx` (should not match; confirms gitignore still parses)
Expected: exits with code 1 (no output), meaning the file is not ignored. This verifies the file parses fine.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: remove stale .gitignore entry for deleted src-tauri directory"
```

---

## Task 6: Release workflow — align Python to minimum supported

**Files:**
- Modify: `.github/workflows/release.yml:59-62` (Python version 3.13 → 3.11)

Rationale: Minimum supported Python is 3.11 (per `pyproject.toml`). Building the release binary against 3.13 means if a user runs it against a 3.11 Python, untested behavior ships. Building against 3.11 produces a binary with 3.11-compatible bytecode that also runs on 3.12 and 3.13.

- [ ] **Step 1: Update the setup-python step**

In `.github/workflows/release.yml`, replace lines 59-62:

```yaml
      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
```

with:

```yaml
      - name: Set up Python (matches pyproject minimum supported)
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
```

Note: CI (`.github/workflows/ci.yml`) still matrix-tests against 3.12 and 3.13, so we keep multi-version coverage on the test path. Only the release binary gets built against 3.11.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: build release binary against Python 3.11 (min supported)"
```

---

## Task 7: Release workflow — macOS switch from `--onefile` to `--onedir` + zip

**Files:**
- Modify: `.github/workflows/release.yml:40-52` (matrix entries — add `onefile-flag` + `artifact-path` per-platform)
- Modify: `.github/workflows/release.yml:93-128` (build step — use `$ONEFILE_FLAG` instead of hardcoded `--onefile`; zip the macOS dist/pii-washer directory)
- Modify: `.github/workflows/release.yml:131-134` (upload step — use `artifact-path`)
- Modify: `.github/workflows/release.yml:148-163` (create-release step — unpack macOS zip path, rename assets)

Rationale: `--onefile` + default macOS settings is already a deprecation warning and becomes a hard error in PyInstaller 7.0 (per CLAUDE.md). macOS is already broken (blank screen) and this is also a step toward unblocking that debug — `--onedir` produces a clearer bundle that's easier to inspect. Windows and Linux stay on `--onefile` to keep UX consistent for currently working platforms.

- [ ] **Step 1: Add per-platform flags to the matrix**

Replace the matrix block (lines 38-52) with:

```yaml
    strategy:
      matrix:
        include:
          - os: windows-latest
            artifact-name: pii-washer-windows
            exe-name: pii-washer.exe
            pyinstaller-args: --name pii-washer --windowed --icon assets/app-icons/pii-washer-app-icon.ico
            onefile-flag: --onefile
            artifact-path: dist/pii-washer.exe
          - os: macos-latest
            artifact-name: pii-washer-macos
            exe-name: pii-washer
            pyinstaller-args: --name pii-washer --icon assets/app-icons/pii-washer-app-icon.icns
            onefile-flag: ""
            artifact-path: dist/pii-washer-macos.zip
          - os: ubuntu-latest
            artifact-name: pii-washer-linux
            exe-name: pii-washer
            pyinstaller-args: --name pii-washer
            onefile-flag: --onefile
            artifact-path: dist/pii-washer
```

- [ ] **Step 2: Update the PyInstaller build step to use the per-platform flag**

In the "Build with PyInstaller" step (around line 93), update the env block and command. Replace:

```yaml
      - name: Build with PyInstaller
        shell: bash
        env:
          PYINSTALLER_ARGS: ${{ matrix.pyinstaller-args }}
        run: |
          SEP=":"
          if [ "$RUNNER_OS" = "Windows" ]; then
            SEP=";"
          fi
          ICON_DATA=""
          if [ -d "icon" ]; then
            ICON_DATA="--add-data icon${SEP}icon"
          fi
          pyinstaller $PYINSTALLER_ARGS \
            --onefile \
            --add-data "ui${SEP}ui" \
```

with:

```yaml
      - name: Build with PyInstaller
        shell: bash
        env:
          PYINSTALLER_ARGS: ${{ matrix.pyinstaller-args }}
          ONEFILE_FLAG: ${{ matrix.onefile-flag }}
        run: |
          SEP=":"
          if [ "$RUNNER_OS" = "Windows" ]; then
            SEP=";"
          fi
          ICON_DATA=""
          if [ -d "icon" ]; then
            ICON_DATA="--add-data icon${SEP}icon"
          fi
          pyinstaller $PYINSTALLER_ARGS \
            $ONEFILE_FLAG \
            --add-data "ui${SEP}ui" \
```

(The rest of the command — the `--add-data`, `--collect-all`, `--hidden-import` lines, and `pyinstaller_entry.py` at the end — is unchanged.)

- [ ] **Step 3: Add a macOS-only zip step before upload**

Insert this step immediately after the "Build with PyInstaller" step and before "Upload build artifact":

```yaml
      - name: Package macOS bundle
        if: runner.os == 'macOS'
        shell: bash
        run: |
          cd dist
          zip -r pii-washer-macos.zip pii-washer
```

This produces `dist/pii-washer-macos.zip`, which matches the matrix `artifact-path` for macOS.

- [ ] **Step 4: Update the upload step to use `artifact-path`**

Replace lines 130-134:

```yaml
      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact-name }}
          path: dist/${{ matrix.exe-name }}
```

with:

```yaml
      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact-name }}
          path: ${{ matrix.artifact-path }}
```

- [ ] **Step 5: Update create-release job to handle the macOS zip**

In the "Prepare release assets" step (line 148-154), replace:

```yaml
      - name: Prepare release assets
        run: |
          mkdir -p release-assets
          cp release-artifacts/pii-washer-windows/pii-washer.exe release-assets/pii-washer-windows.exe
          cp release-artifacts/pii-washer-macos/pii-washer release-assets/pii-washer-macos
          cp release-artifacts/pii-washer-linux/pii-washer release-assets/pii-washer-linux
          chmod +x release-assets/pii-washer-macos release-assets/pii-washer-linux
```

with:

```yaml
      - name: Prepare release assets
        run: |
          mkdir -p release-assets
          cp release-artifacts/pii-washer-windows/pii-washer.exe release-assets/pii-washer-windows.exe
          cp release-artifacts/pii-washer-macos/pii-washer-macos.zip release-assets/pii-washer-macos.zip
          cp release-artifacts/pii-washer-linux/pii-washer release-assets/pii-washer-linux
          chmod +x release-assets/pii-washer-linux
```

Then update the files list in the "Create GitHub Release" step (lines 160-163):

```yaml
          files: |
            release-assets/pii-washer-windows.exe
            release-assets/pii-washer-macos.zip
            release-assets/pii-washer-linux
```

- [ ] **Step 6: Lint the YAML locally**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`
Expected: no output (YAML parses cleanly)

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: switch macOS build to --onedir + zip (avoids PyInstaller 7.0 break)"
```

---

## Task 8: Release workflow — annotate hidden imports + add Linux smoketest

**Files:**
- Modify: `.github/workflows/release.yml:114-127` (add inline comments explaining each `--hidden-import`)
- Modify: `.github/workflows/release.yml` (add a new "Smoke test built binary" step for Linux only)

Rationale: The 14 `--hidden-import` entries exist because PyInstaller's static analyzer can't always infer them (e.g. Presidio and spaCy use dynamic imports). If one gets pruned in the future, PyInstaller still builds successfully — the failure only surfaces at runtime. Two mitigations: (a) annotate each so maintainers know *why* it's there, (b) run the built Linux binary briefly and confirm it starts the API server. Linux is the cheapest platform to smoketest in CI; Windows needs GUI. macOS is broken for now.

The smoketest uses `pyinstaller_entry.py` starting its FastAPI server, then a `curl` against `/api/v1/health`. If any hidden import is missing, the import chain at startup will throw and the health check will fail.

- [ ] **Step 1: Annotate hidden imports**

In `.github/workflows/release.yml`, in the `pyinstaller` command, replace the hidden-import block (the block of 14 `--hidden-import` lines) with:

```bash
          pyinstaller $PYINSTALLER_ARGS \
            $ONEFILE_FLAG \
            --add-data "ui${SEP}ui" \
            --add-data "pii_washer/data${SEP}pii_washer/data" \
            $ICON_DATA \
            --collect-all en_core_web_lg \
            --collect-data tldextract \
            --collect-data presidio_analyzer \
            `# Explicit imports — PyInstaller can't always discover these statically.` \
            `# pii_washer.* : package and submodules used by entry point` \
            --hidden-import pii_washer \
            --hidden-import pii_washer.api \
            --hidden-import pii_washer.api.main \
            --hidden-import pii_washer.extractors \
            --hidden-import pii_washer.extractors.docx \
            --hidden-import pii_washer.extractors.pdf \
            --hidden-import pii_washer.extractors.csv_ext \
            --hidden-import pii_washer.extractors.xlsx \
            --hidden-import pii_washer.extractors.html \
            `# Third-party deps with dynamic import patterns` \
            --hidden-import pdfplumber \
            --hidden-import pdfminer \
            --hidden-import docx \
            --hidden-import openpyxl \
            --hidden-import bs4 \
            pyinstaller_entry.py
```

Note: bash treats backtick-prefixed lines as comments (command substitution of an empty echo). This is the least-invasive way to annotate YAML-embedded shell. If the runner complains, replace `` ` ... ` \`` with `# ...` on their own lines — but backtick form preserves line continuation without needing an echo.

Actually — backticks DO execute as command substitution. Use a different comment pattern: insert bash comments with `true # comment` pattern, or just put the comments as regular bash comments on their own lines (no backslash). Simpler approach — use bash comments broken out of the backslash chain:

```bash
          # PyInstaller hidden imports:
          #   pii_washer.*        — package and submodules used by entry point
          #   pdfplumber/pdfminer — pdf extractor
          #   docx                — python-docx (docx extractor)
          #   openpyxl            — xlsx extractor
          #   bs4                 — html extractor (beautifulsoup4)
          # If any are removed, the build still succeeds but runtime imports fail.
          # The Linux smoke test below will catch runtime-import regressions.
          pyinstaller $PYINSTALLER_ARGS \
            $ONEFILE_FLAG \
            --add-data "ui${SEP}ui" \
            --add-data "pii_washer/data${SEP}pii_washer/data" \
            $ICON_DATA \
            --collect-all en_core_web_lg \
            --collect-data tldextract \
            --collect-data presidio_analyzer \
            --hidden-import pii_washer \
            --hidden-import pii_washer.api \
            --hidden-import pii_washer.api.main \
            --hidden-import pii_washer.extractors \
            --hidden-import pii_washer.extractors.docx \
            --hidden-import pii_washer.extractors.pdf \
            --hidden-import pii_washer.extractors.csv_ext \
            --hidden-import pii_washer.extractors.xlsx \
            --hidden-import pii_washer.extractors.html \
            --hidden-import pdfplumber \
            --hidden-import pdfminer \
            --hidden-import docx \
            --hidden-import openpyxl \
            --hidden-import bs4 \
            pyinstaller_entry.py
```

Place the comment block *immediately above* the `pyinstaller` line so it's clearly documentation for the command.

- [ ] **Step 2: Add a Linux-only smoke test step**

Insert this step immediately after the "Upload build artifact" step (currently lines 130-134), so it runs only on the Linux job. Use `if: runner.os == 'Linux'`:

```yaml
      - name: Smoke test Linux binary (verifies hidden imports at runtime)
        if: runner.os == 'Linux'
        shell: bash
        run: |
          # Launch the binary as a background process, then hit /api/v1/health.
          # If any hidden import is missing, the FastAPI startup will fail
          # and the health check will never succeed.
          chmod +x dist/pii-washer
          dist/pii-washer &
          APP_PID=$!
          # Give the server time to start (spaCy model load + FastAPI boot)
          for i in $(seq 1 60); do
            if curl -fs http://127.0.0.1:8000/api/v1/health > /tmp/health.json 2>/dev/null; then
              echo "Health check passed:"
              cat /tmp/health.json
              kill $APP_PID 2>/dev/null || true
              exit 0
            fi
            sleep 2
          done
          echo "Smoke test FAILED: /api/v1/health never responded within 120s"
          kill $APP_PID 2>/dev/null || true
          exit 1
```

Notes:
- 60 attempts × 2s = 120s. The spaCy `en_core_web_lg` model takes ~20-40s to load on a CI runner; this buffers for that.
- `dist/pii-washer` is the Linux onefile binary produced by PyInstaller, which is also the `artifact-path` for Linux after Task 7.
- The step runs before the upload artifact step would be reached on Linux; we place it after upload so the artifact is still uploaded even if smoketest fails, so a human can inspect it.

Actually — re-thinking: place it *before* upload would block a broken build from being uploaded. But placing it *after* upload means we still get the artifact for debugging when it fails. Choose the second: **after upload**, so we always get the artifact for post-mortem.

- [ ] **Step 3: Lint the YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: annotate hidden imports and smoke-test Linux release binary"
```

---

## Task 9: Final verification

- [ ] **Step 1: Rerun full test suite**

Run: `pytest -q`
Expected: PASS

Run: `cd pii-washer-ui && npm run build && npm run lint && npm run test`
Expected: PASS

- [ ] **Step 2: Review the commit history**

Run: `git log --oneline main..HEAD`
Expected: 7 commits, one per task, each a focused concern.

- [ ] **Step 3: Review the net diff**

Run: `git diff main..HEAD --stat`
Expected: changes concentrated in `pii_washer/api/`, `pii_washer/session_manager.py`, `pii-washer-ui/src/`, `.github/workflows/release.yml`, `.gitignore`, `CLAUDE.md`. No surprise files touched.

- [ ] **Step 4: Push and watch CI**

Run: `git push origin main`

Expected: CI workflow runs on push and passes. Release workflow does NOT run (no tag pushed). If you want to manually verify the release workflow, push a throwaway tag like `v1.2.0-test` and delete it after.

---

## Self-review checklist

- [x] **Spec coverage:** All three decisions (A/A/A) covered. Version consolidation = Task 1. Tauri CORS + dead code sweeps = Tasks 2–5. Release hardening = Tasks 6–8.
- [x] **No placeholders:** All code shown in full, all commands concrete, all file paths exact.
- [x] **Type consistency:** `get_app_version()` used identically across config.py, main.py, router.py. Matrix `onefile-flag` and `artifact-path` consistent across all three platform entries.
- [x] **Risk flags:** Task 7 macOS zip step and Task 8 smoke test are the only untested-in-CI-yet changes; the self-test via `python -c "import yaml"` + a throwaway tag push are the verification path.
