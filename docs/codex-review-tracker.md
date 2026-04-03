# Codex Adversarial Review — Full Tracker

**Review date:** 2026-04-02
**Reviewer:** Codex (full-codebase adversarial review)
**Total findings:** 22 (12 fixed, 1 won't fix, 4 mitigated, 5 not applicable)

This is the single source of truth for every finding from the Codex adversarial review. Nothing gets "deferred to roadmap" without staying on this list. Every item stays here until it's **done** or explicitly marked **won't fix** with a reason.

---

## Status Key

| Status | Meaning |
|--------|---------|
| **Fixed** | Code change shipped |
| **Open** | Still an issue, needs work |
| **Mitigated** | Partial fix in place, could be improved |
| **Won't fix** | Deliberately accepted with documented reason |
| **N/A** | Not applicable to this project's threat model (local single-user tool) |

---

## Fixed (8)

All shipped in PR #3 on 2026-04-02.

| # | Finding | What was done | Files changed |
|---|---------|---------------|---------------|
| 1 | `original_text` in session creation response | Removed field from `SessionCreatedResponse` — PII no longer round-trips in browser caches | `api/models.py`, `api/router.py`, `tests/test_api.py`, `ui/types/api.ts` |
| 2 | `GET /sessions/{id}` returns raw untyped dict | Added `SessionDetailResponse` Pydantic model — prevents accidental field leaks | `api/models.py`, `api/router.py` |
| 3 | Server error response leaks exception details | Generic "An unexpected error occurred" message — full details stay in log file | `api/errors.py` |
| 4 | CORS allows all methods and headers | Restricted to `GET, POST, PATCH, OPTIONS` and `Content-Type` only | `api/main.py` |
| 5 | httpx client connection leak in update checker | Wrapped in `async with` context manager | `api/update_checker.py` |
| 6 | No validation on custom placeholder content | Added character allowlist and 50-char max length | `session_manager.py` |
| 7 | ALL CAPS names not detected | Updated `DictionaryNameRecognizer` and `TitleNameRecognizer` to accept all-caps | `name_recognizer.py` |
| 8 | Error message says "10 MB" but limit is 1 MB | Corrected to "1 MB" | `ui/InputTab.tsx` |

---

## Fixed — Batch 2 (4, shipped 2026-04-03)

| # | Finding | What was done | Files changed |
|---|---------|---------------|---------------|
| 9 | No React error boundaries | Installed `react-error-boundary`, created `AppErrorBoundary` component wrapping `<AppShell />`, shows friendly error message with "Start Over" button that resets store. Toaster stays outside boundary. | `ui/App.tsx`, `ui/components/ErrorBoundary.tsx` |
| 10 | No frontend tests | Installed vitest + testing-library + jsdom, configured in vite.config.ts, added test setup. 8 tests: 5 for Zustand store (state transitions, reset), 3 for ErrorBoundary (render, error display, recovery). | `ui/vite.config.ts`, `ui/package.json`, `ui/src/test/setup.ts`, new test files |
| 11 | No integration tests with real Presidio through API | Created `test_api_integration.py` with 4 tests exercising full HTTP→FastAPI→SessionManager→PIIDetectionEngine flow. Skips gracefully if spaCy model not installed. Marked `@pytest.mark.integration`. | `tests/test_api_integration.py`, `pyproject.toml` |
| 12 | PLACEHOLDER_PATTERN misses custom placeholders | `repersonalize()` now builds a dynamic scan from the session's actual placeholder list in addition to the hardcoded pattern. Custom-edited placeholders are now reported in `unknown_in_text`. | `text_substitution_engine.py` |

## Won't Fix (1)

| # | Finding | Reason |
|---|---------|--------|
| 13 | App state lost on browser refresh | By design. The "paste-wash-done" workflow is intentionally disposable. Persisting session state adds attack surface (PII in browser storage) with no UX benefit. |

---

## Mitigated — Could Be Improved (4)

### 14. `secure_clear()` doesn't erase Python strings from memory

**Severity:** Low for a local-only tool — an attacker with memory access to your machine has bigger problems.
**Current state:** `_recursive_wipe()` walks nested dicts/lists, replaces string values with `""`, then calls `.clear()`. This removes references so GC can reclaim sooner. But immutable Python strings stay in memory until the allocator reuses that space.
**What's left:** Adding `gc.collect()` after `secure_clear()` would be a small pragmatic improvement. True zeroing would require `ctypes` (fragile, CPython-specific) or storing PII in `bytearray` instead of `str` (major refactor).
**Recommendation:** Add `gc.collect()`. Document the Python limitation. Accept this as a known constraint.
**Files:** `pii_washer/temp_data_store.py`

### 15. Date false positives at low confidence

**Severity:** Low — dates without context surface at 0.2 confidence (the minimum threshold), so they appear as suggestions the user can dismiss.
**Current state:** `_has_dob_context()` checks for DOB-related keywords within 100 chars. Dates without context get forced to 0.2 confidence. The user sees them but can dismiss.
**What's left:** Could raise the DATE_TIME-specific threshold slightly above 0.2 to auto-drop context-less dates, or add a separate `date_confidence_threshold` config option.
**Recommendation:** Current behavior is arguably correct — surfacing dates for review is safer than hiding them. Revisit if users report noise.
**Files:** `pii_washer/pii_detection_engine.py`

### 16. CapitalizedPairRecognizer false positive rate

**Severity:** Low — confidence is 0.3, so these surface as low-confidence suggestions.
**Current state:** Multiple filter layers added: sentence-start skip, bracket skip, exclusion lists (`capitalized_word_exclusions.json`), org suffix skip, field label skip.
**What's left:** Expand exclusions as new false positives are discovered. Could require at least one word to match the first-names dictionary (but that would change the recognizer's purpose).
**Recommendation:** Keep expanding the exclusion list over time. The 0.3 confidence means users can easily dismiss false positives.
**Files:** `pii_washer/name_recognizer.py`, `pii_washer/capitalized_word_exclusions.json`

### 17. International PII formats not detected

**Severity:** Low for current scope — the app is explicitly US/English-focused.
**Current state:** All custom recognizers are US-only. Phone = NANP format. SSN = US format. Addresses = US street types, states, ZIP codes. spaCy model = `en_core_web_lg`.
**What's left:** This is a feature, not a fix. Each country needs its own recognizers (UK NIN, Canadian SIN, EU phone formats, etc.). Would also need additional spaCy models for non-English NER.
**Recommendation:** Document US/English scope in README. Tackle international support as a dedicated feature when there's demand.
**Files:** `pii_washer/pii_detection_engine.py`, `pii_washer/name_recognizer.py`

---

## Not Applicable (5)

These were flagged by the review but don't apply to PII Washer's threat model (local single-user desktop tool, no network exposure, no concurrent users).

| # | Finding | Why N/A |
|---|---------|---------|
| 18 | No rate limiting | Local tool — no external API exposure, no untrusted clients |
| 19 | Session ID entropy too low | Single-user tool — no session hijacking risk |
| 20 | Race conditions on concurrent requests | Single-user — no concurrent request scenarios |
| 21 | Internal data representation uses dicts instead of typed objects | Code quality preference, not a security or correctness issue |
| 22 | File size check happens after upload buffering | Streamlit finding from v1.0 — app is now FastAPI + React, upload handling changed. 1MB limit is enforced in both frontend (JS check) and backend (`DocumentLoader`). Memory impact of buffering a file slightly over 1MB is negligible for a local tool. |

---

## Summary

| Status | Count |
|--------|-------|
| Fixed (batch 1, PR #3) | 8 |
| Fixed (batch 2, 2026-04-03) | 4 |
| Won't fix | 1 |
| Mitigated — could improve | 4 |
| Not applicable | 5 |
| **Total** | **22** |

## Next Actions

All actionable findings are resolved. The 4 **Mitigated** items (#14-17) are known limitations with partial fixes in place — they can be revisited as part of their respective roadmap items if needed.
