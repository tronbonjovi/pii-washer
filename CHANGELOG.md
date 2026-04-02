# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
