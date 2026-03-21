# ADR 001: Field Label False Positive Strategy

**Date:** 2026-03-20
**Status:** Accepted

## Context

CapitalizedPairRecognizer flags any 2-3 adjacent capitalized words as potential person names (at 0.3 confidence). This causes false positives on form field labels like "Full Name", "Phone Number", and "Email Address" when users paste structured text containing those labels.

The pipeline feeds raw text flat into all recognizers — there is no pre-processing to identify structured formats or separate labels from values.

## Decision

Use two complementary filters rather than either alone:

1. **Explicit exclusion list** — A `form_field_labels` category in `capitalized_word_exclusions.json` with common field labels. These are filtered by the existing multiword exclusion check in CapitalizedPairRecognizer.

2. **Colon-context filter** — Suppress any capitalized pair immediately followed by `:` in the source text, since that pattern strongly signals a label, not a name.

## Alternatives Considered

- **Exclusion list only:** Would miss labels we didn't think to list. New form formats would need manual updates.
- **Colon filter only:** Would miss labels not followed by colons (e.g., "enter your Full Name below").
- **Structured text pre-processing:** Parsing key-value pairs before detection. Much heavier, would require changes to the document loader and detection pipeline. Not justified by the scope of the problem.

## Consequences

- Known labels are caught explicitly regardless of surrounding context.
- Unknown labels followed by colons are caught generically.
- Labels without colons that aren't in the exclusion list will still be false positives — the list should grow as new cases are reported.
- No changes to the detection pipeline architecture. The fix is local to CapitalizedPairRecognizer and its data file.
