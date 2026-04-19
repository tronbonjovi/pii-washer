# Pii Washer — Roadmap

**Last updated:** 2026-04-18
**Status:** Active — living document, updated as milestones ship

This roadmap frames the work ahead for Pii Washer. Milestones go through a brainstorm → plan → execute flow; shipped milestones move to the Completed table with a short note.

---

## Completed

| Milestone | Description | Shipped |
|---|---|---|
| Detection refinement | Improved handling of typos, malformed formats, edge cases | 2026-03-18 |
| Document viewer text selection | Allow selecting/copying text in the analyzed document viewer | 2026-03-18 |
| Bug fix batch | Upload metadata persistence, file size limit alignment, perf, render bugs | 2026-03-27 |
| Session removal (v1.1.0) | Removed multi-session UI; "Start Over" replaces session management | 2026-04-01 |
| Codex review remediation | API hardening + ALL CAPS name detection + UI bug fix (PR #3) | 2026-04-02 |
| Dependency documentation | US/English-only scope disclaimer; dead Tauri deps removed; tsconfig fixes | 2026-04-03 |
| Additional file formats | `.docx`, `.pdf`, `.csv`, `.xlsx`, `.html` via extractor architecture | 2026-04-03 |
| Cross-platform release builds (v1.2.0) | GitHub Actions CI + release workflow for Win/Mac/Linux executables | 2026-04-03 |
| **Milestone 1 — Housekeeping & release hardening** | Version consolidation via `importlib.metadata`, dead-code sweep (Tauri CORS, orphaned SessionManager methods, unused frontend code), release workflow fixes (Python 3.11, macOS `--onedir`, Linux smoke test). Plan: `docs/superpowers/plans/2026-04-18-housekeeping-release-hardening.md`. | 2026-04-18 |
| **Milestone 2 — Correctness pass** | Typed API exceptions replacing string-matched ValueErrors, MAX_FILE_SIZE layering fix, ResponseTab state-sync bug, useResetSession targeted invalidation, NoSessionAlert dedup. Plan: `docs/superpowers/plans/2026-04-18-milestone-2-correctness.md`. | 2026-04-18 |

---

## Near-term — Polish & trust

| Milestone | Description | Status |
|---|---|---|
| **Milestone 3 — Accessibility pass** | ARIA labels on interactive elements (copy button success state, placeholder edit inputs), `focus-visible` rings on header nav, keyboard-navigation gaps. Target WCAG AA. | TBD — needs brainstorm session |
| Security assessment | WebView2 disk caching, clipboard persistence, PyInstaller temp dir behavior. Runtime/platform-level concerns. Also: Codex tracker #14 (`secure_clear` memory limits). | TBD — needs brainstorm session |

## Medium-term — Infra & platform

| Item | Description | Status |
|---|---|---|
| GitHub Actions Node 20 → Node 24 upgrade | `actions/checkout@v4`, `actions/setup-node@v4`, `actions/cache@v4`, `actions/setup-python@v5` are all flagged. Forced upgrade starts 2026-06-02, Node 20 removed 2026-09-16. Either bump actions to Node-24-compatible versions or set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` env var workflow-wide. | TBD — low-urgency but dated |
| macOS executable debugging | Blank white screen on macOS — pywebview + WebKit + PyInstaller bundling issue. Milestone 1 switched to `--onedir` which may help inspect the bundle. Still needs macOS dev environment to debug. | TBD — blocked on macOS dev setup |
| Code signing | Sign the Windows exe to eliminate SmartScreen warnings. Requires purchasing a code signing certificate ($100–400/yr). | TBD — revisit when there's a user base |
| Detection improvements v2 | International PII, date false positives, CapitalizedPairRecognizer tuning. See Codex tracker #15–17. One gap surfaced during milestone 2 local test run: Presidio 2.2.362 doesn't detect `(555) 123-4567` phone format. | TBD — needs brainstorm session |
| UX polish batch | Toast positioning, button placement, detection summary sizing, text field readability. Also Codex tracker #9 (error boundaries) and #13 (state persistence on refresh). | TBD — needs brainstorm session |
| Logo & icon updates | Fix ico file sizes (small icons show default), add transparent backgrounds. | TBD — needs brainstorm session |
| Test infrastructure | Broader frontend test coverage and Presidio integration tests in CI. See Codex tracker #10–11. | TBD — needs brainstorm session |
| Bug triage process | Structured intake → reproduce → fix → verify loop. More valuable once user base grows. | TBD — needs brainstorm session |

## Long-term — New platforms

| Item | Description | Status |
|---|---|---|
| Mobile apps | Native or cross-platform mobile support. Blocked by Python NLP stack (spaCy + Presidio) not running on iOS/Android — would require rebuilding the detection engine, not a port. | Deferred |

---

## How this roadmap works

- No fixed order — pull from whichever bucket makes sense at the time.
- Each milestone gets a brainstorming session before implementation begins.
- Brainstorming sessions produce design specs, which become implementation plans under `docs/superpowers/plans/`.
- Shipped milestones move to the Completed table with a link to their plan doc.
- This document is updated at the end of each session that closes a milestone.
