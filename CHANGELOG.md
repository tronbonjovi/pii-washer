# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Typed API exception classes in `pii_washer/api/exceptions.py` (`InvalidStateError`, `DetectionNotFoundError`, `DuplicateDetectionError`, `TextNotFoundError`) — each carries its own HTTP status and error code instead of being inferred from the error message
- `get_app_version()` in `pii_washer/api/config.py` reads the version from installed package metadata — single source of truth in `pyproject.toml`
- `NoSessionAlert` component for consistent empty-state UX across tabs
- Release binary smoke test: on Linux, the built executable is launched under `xvfb-run` and polled via `/api/v1/health` — catches missing PyInstaller `--hidden-import` entries before a release ships

### Changed

- `MAX_FILE_SIZE` moved from `DocumentLoader` class attribute to `pii_washer/api/config.py`; router no longer imports `DocumentLoader` just for the constant
- Release workflow builds against Python 3.11 (minimum supported) instead of 3.13, so release bytecode is compatible with the full 3.11/3.12/3.13 range
- macOS release uses `--onedir` + zipped bundle instead of `--onefile` (avoids PyInstaller 7.0 breakage)
- `useResetSession` now targets session-scoped query keys (`['session']`, `['sessionStatus']`, `['sessions']`) instead of clearing the entire React Query cache

### Fixed

- `ResponseTab` re-syncs its textarea when the server `response_text` changes while the session stays in `awaiting_response` — previously stuck on stale content in that edge case

### Removed

- Tauri CORS origins from `CORS_ORIGINS` (Tauri was removed from the project long ago)
- Orphaned `SessionManager` methods: `get_depersonalized_text`, `load_response_file`
- Dead frontend files: `App.css` (Vite scaffolding), `api/health.ts`, unused `useAnalyze` hook
- Stale `.gitignore` entry for `pii-washer-ui/src-tauri/`
- Dummy `"version": "0.0.0"` from frontend `package.json`
- Stale `__version__ = "1.0.0"` from `pii_washer/__init__.py` (the `APP_VERSION` in `config.py` was kept in sync with `pyproject.toml`; both are now replaced by `get_app_version()`)

## [1.2.0] - 2026-04-03

### Added

- File format support: .docx, .pdf, .csv, .xlsx, .html
- Extractor architecture in `pii_washer/extractors/` with strategy pattern
- Structure preservation: headings, paragraphs, lists, and tables maintained in extracted text
- CI workflow: backend tests (Python 3.12/3.13), Ruff lint, frontend lint/build/test on every push/PR
- Cross-platform release builds: Windows, macOS, and Linux executables via GitHub Actions

## [1.1.1] - 2026-04-03

### Added

- Settings menu (gear icon) in header with About dialog and Check for Updates
- `GET /api/v1/updates/check` endpoint for version comparison against GitHub releases
- ALL CAPS name detection in `DictionaryNameRecognizer` and `TitleNameRecognizer`
- Typed `SessionDetailResponse` Pydantic model for `GET /sessions/{id}`
- Custom placeholder validation (character allowlist, 50-char max)
- React error boundary — app shows friendly error screen with "Start Over" instead of going blank
- Frontend test infrastructure (vitest + testing-library) with store and component tests
- API integration tests with real Presidio/spaCy (skips gracefully if model not installed)
- Codex adversarial review tracker (`docs/codex-review-tracker.md`) — single source of truth for all 22 findings

### Fixed

- Session creation response no longer includes `original_text` (reduces PII exposure in browser caches)
- Server error responses no longer leak internal exception details
- CORS restricted to only used methods and headers
- httpx client connection leak in update checker
- File size error message corrected from "10 MB" to "1 MB"
- Custom-edited placeholders now detected in `unknown_in_text` report during repersonalization

## [1.1.0] - 2026-04-01

### Added

- "Start Over" button in header to reset and begin a new task
- `POST /sessions/reset` endpoint for clearing session state

### Removed

- Session list, import/export, and multi-session management UI
- Backend endpoints: `GET /sessions`, `DELETE /sessions`, `POST /sessions/import`, `DELETE /sessions/{id}`, `GET /sessions/{id}/export`

## [1.0.1] - 2026-03-20

### Added

- Dictionary-based and heuristic name recognizers for improved PII name detection
- Error logging to `~/.pii-washer/pii-washer.log` with full tracebacks
- Integration and false positive test coverage

### Fixed

- Reduced false positives in name detection (bracketed text, newline bleed)
- ZIP code, phone number, and IP address validation accuracy
- Export toast no longer covers action buttons
- Text selection now works in the Review tab document viewer
- Path traversal guard on file operations
- Security review findings (session data handling, input validation)
- Removed ghost "confirmed" status that was accepted by the data store but never used by the workflow engine
- Declared missing `tldextract` dependency; added `pywebview` as optional desktop extra

### Changed

- Removed abandoned Tauri build artifacts from the frontend directory

## [1.0.0] - 2026-03-18

Initial public release. Local-only PII detection and text sanitization with a React UI and FastAPI backend.
