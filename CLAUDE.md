# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. This repo is **private** — safe to include dev notes, plans, and AI instructions here.

## Development Environments

Three machines share this repo. Always `git pull` before starting work.

| Machine | OS | Primary use | Notes |
|---|---|---|---|
| Linux devbox | Ubuntu (SSH) | Main development | Primary workflow, accessed via terminal from Windows or Mac |
| Windows desktop | Windows 11 | Testing Windows exe | Also has VS Code / VSCodium with Remote SSH to devbox |
| MacBook Pro | macOS | Testing macOS exe, debugging macOS issues | New — being set up for macOS-specific work |

**Sync rule:** Git is the single source of truth. No manual syncing. Push when done, pull when starting. CLAUDE.md carries project context so any environment can pick up where the last left off.

**What doesn't sync:** The `.claude/` directory (memory, local settings) is per-machine. Each environment has its own Claude Code memory. Project context that matters across environments goes in this file or in `docs/`.

## Project Overview

PII Washer is a local-only PII detection and text sanitization tool. Users paste text containing personal data, get a clean version with placeholders, use it with LLMs, then swap placeholders back. Privacy-first: no network calls, in-memory only, secure clear on shutdown.

## Commands

```bash
# Backend
pip install -e ".[dev]"                    # Install with dev deps (pytest, httpx)
uvicorn pii_washer.api.main:app --reload   # Run backend on :8000

# Frontend
cd pii-washer-ui && npm install            # Install frontend deps
cd pii-washer-ui && npm run dev            # Run frontend on :5173
cd pii-washer-ui && npm run lint           # ESLint
cd pii-washer-ui && npm run build          # TypeScript check + Vite build

# Tests
pytest                                     # Run all backend tests
pytest pii_washer/tests/test_api.py        # Run a single test file
pytest -k "test_depersonalize"             # Run tests matching a name
```

## Architecture

**Backend (Python):** FastAPI REST API at `/api/v1/`. All components are wired through `SessionManager`, which is the single orchestration boundary — the API router calls only SessionManager methods.

- `SessionManager` — coordinates workflow through a state machine (`user_input` → `analyzed` → `depersonalized` → `awaiting_response` → `repersonalized`). Each state gates which operations are allowed via `WORKFLOW_STATES`.
- `PIIDetectionEngine` — wraps Microsoft Presidio + spaCy NER (`en_core_web_lg`) with custom regex recognizers for formats Presidio misses.
- `PlaceholderGenerator` — deterministic `[TYPE_N]` placeholder assignment with a `CATEGORY_PREFIX_MAP`.
- `TextSubstitutionEngine` — bidirectional: depersonalize (PII → placeholders) and repersonalize (placeholders → PII).
- `TempDataStore` — in-memory session storage with secure clear.
- `DocumentLoader` — text/file ingestion with validation. 1MB file size limit. Allowed extensions: `.txt`, `.md`, `.docx`, `.pdf`, `.csv`, `.xlsx`, `.html`. Binary formats use extractors in `pii_washer/extractors/`.

**Frontend (React 19 + TypeScript + Vite + Tailwind v4):** SPA in `pii-washer-ui/`. Uses Zustand for state, TanStack React Query for API calls, Radix UI primitives, and Lucide icons. Tab-based workflow: Input → Review → Response → Results. API client in `src/api/client.ts`.

**Desktop:** PyInstaller + pywebview. Entry point at `pyinstaller_entry.py` — starts FastAPI in a background thread, opens a native window via pywebview. The frontend dist is bundled at `ui/` inside the executable.

## Key Constraints

- **Python 3.11–3.13 only.** Python 3.14 is incompatible (spaCy's pydantic v1 dependency).
- **spaCy model installed via direct URL**, not `spacy download`: `pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl`
- **Never write PII to disk.** File uploads are decoded in memory. Session data is in-memory only.
- **Tests use a MockDetectionEngine** that returns predictable detections without requiring spaCy/Presidio. The real engine is heavy (~560MB model) and slow to initialize.
- The `create_app()` factory in `api/main.py` accepts an optional `session_manager` for test injection.
- **Version has a single source of truth: `pyproject.toml`.** The API reads it at runtime via `importlib.metadata.version("pii-washer")` (see `get_app_version()` in `pii_washer/api/config.py`). Only update `pyproject.toml` when bumping.

## CI / Release Pipeline

**CI** (`.github/workflows/ci.yml`): Runs on every push/PR to main.
- Backend: Ruff lint + pytest on Python 3.12 and 3.13 matrix
- Frontend: ESLint + TypeScript build + vitest
- Tests that require spaCy model (`test_pii_detection_engine.py`, `test_name_recognizer.py`) are excluded from CI

**Release** (`.github/workflows/release.yml`): Triggered by pushing a `v*` tag.
1. Builds frontend once on Ubuntu
2. Builds PyInstaller desktop executables for Windows, macOS, and Linux in parallel
3. Uploads all three as GitHub Release assets via `softprops/action-gh-release`

```bash
# To create a release:
git tag v1.x.x
git push origin v1.x.x
# ~8 minutes later, release appears at GitHub with 3 executables
```

**Known platform issues:**
- **Windows:** Works. Uses `--windowed` flag (no terminal). SmartScreen warning expected without code signing.
- **macOS:** Broken (blank white screen). PyInstaller `--onefile` + pywebview/WebKit bundling issue. Needs macOS dev environment to debug. `--windowed` is incompatible with `--onefile` on macOS (PyInstaller deprecation warning, becomes error in v7.0).
- **Linux:** Works. Opens terminal alongside GUI window (no `--windowed`).
