# Pii Washer — Roadmap

**Created:** March 18, 2026
**Last updated:** April 3, 2026
**Status:** Active — living document, updated as brainstorming sessions take place

This roadmap frames the work ahead for Pii Washer. Items are grouped by time horizon, not version number. Each item gets its own brainstorming/design session when picked up — sequencing is flexible within each bucket, but the suggested order reflects logical dependencies.

---

## Completed

| Item | Description | Completed |
|---|---|---|
| Detection refinement | Improved handling of typos, malformed formats, edge cases in PII detection | 2026-03-18 |
| Document viewer text selection | Allow selecting/copying text in the analyzed document viewer | 2026-03-18 |
| Bug fix batch | Upload metadata persistence, file size limit alignment, city regex perf, ResponseTab render fix, blob URL timing, Confirm All edit lock | 2026-03-27 |
| Session removal | Removed user-facing session management. Single-session utility with "Start Over" button. Released as v1.1.0. | 2026-04-01 |
| Codex review remediation | API hardening (6 fixes) + ALL CAPS name detection + UI bug fix. Driven by full-codebase Codex adversarial review. PR #3. Full tracker: `docs/codex-review-tracker.md` (5 open, 4 mitigated, 5 N/A remaining). | 2026-04-02 |

## Near-term — Simplify and polish

Suggested order reflects dependencies (session removal changes the UI surface, so UX work should follow it).

| # | Item | Description | Status |
|---|---|---|---|
| ~~1~~ | ~~Session removal~~ | ~~Completed — see Completed table~~ | ~~Done~~ |
| 2 | UX polish batch | Toast positioning, button placement, detection summary sizing, text field readability. Also includes Codex tracker #9 (error boundaries) and #13 (state persistence on refresh). | TBD — needs brainstorm session |
| 3 | Logo & icon updates | Fix ico file sizes (small icons show default), add transparent backgrounds | TBD — needs brainstorm session |
| 4 | Security assessment | Investigate WebView2 disk caching, clipboard persistence, PyInstaller temp dir behavior. Runtime/platform-level concerns. See also Codex tracker #14 (`secure_clear` memory limits). | TBD — needs brainstorm session |
| 5 | Dependency documentation | Document all dependencies and their roles. Transparent disclaimers about what the tool does and doesn't guarantee. | TBD — needs brainstorm session |

## Medium-term — Expand capabilities

| Item | Description | Status |
|---|---|---|
| Cross-platform release builds | GitHub Actions workflow that builds Windows, macOS, and Linux executables on release and uploads them as assets | TBD — needs brainstorm session |
| Code signing | Sign the Windows exe to eliminate SmartScreen warnings. Requires purchasing a code signing certificate ($100-400/yr). | TBD — worth revisiting once there's a user base |
| Additional file formats | Support beyond .txt and .md | TBD — needs brainstorm session |
| Detection improvements v2 | International PII, date false positives, CapitalizedPairRecognizer tuning. See Codex tracker #15-17 for current state and what's already mitigated. | TBD — needs brainstorm session |
| Test infrastructure | Frontend tests and Presidio integration tests. See Codex tracker #10-11 for details. | TBD — needs brainstorm session |
| Bug triage process | Structured workflow for reviewing and addressing bug reports. Intake -> reproduce -> fix -> verify loop. | TBD — needs brainstorm session (more valuable once user base grows) |

## Long-term — New platforms

| Item | Description | Status |
|---|---|---|
| Mobile apps | Native or cross-platform mobile support. Blocked by the fact that the Python NLP stack (spaCy + Presidio) doesn't run on iOS/Android — would require a full detection engine rebuild, not a port. | Deferred — not viable without significant rework |
| TBD | Additional ideas as they emerge | — |

---

## How this roadmap works

- No fixed order — pull from whichever bucket makes sense at the time.
- Each item gets a brainstorming session before implementation begins.
- Brainstorming sessions produce design specs, which then become implementation plans.
- This document is updated as items are picked up, designed, and completed.
- This roadmap is tracked in the repo at `docs/roadmap.md`.
