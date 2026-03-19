# Detection Refinement — Design Spec

**Date:** 2026-03-18
**Scope:** Detection engine only (no UI changes)
**Philosophy:** Catch more, review more — the cost of a miss (PII leaks to AI) is higher than the cost of a false positive (user clicks reject)
**Region:** US-only for now

---

## 1. Name Detection Fallback Layer

spaCy NER is the only current path for name detection. When it misses obvious names (e.g., "Jane Doe"), nothing catches them. Add three fallback layers that run alongside NER via custom Presidio recognizers.

### 1a. Title-Based Name Detection

**Pattern:** Title prefix followed by 1-3 capitalized words.

Titles: Mr, Mrs, Ms, Miss, Dr, Prof, Professor, Rev, Reverend, Sr, Jr, Sgt, Sergeant, Cpl, Corporal, Pvt, Private, Lt, Lieutenant, Capt, Captain, Maj, Major, Col, Colonel, Gen, General, Hon, Honorable, Judge, Justice, Sen, Senator, Rep, Representative, Gov, Governor, Pres, President

Each title matches with or without a trailing period. Pattern example:
```
\b(?:Mr|Mrs|Ms|Miss|Dr|Prof(?:essor)?|...)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b
```

**Confidence:** 0.7
**Entity type:** `PERSON` (maps to `NAME`)

### 1b. Common First Name Dictionary

**Data source:** US Census derived list of ~1000 most common first names (covering ~90% of the US population). Stored as `pii_washer/data/common_first_names.json`.

**Pattern:** A word from the dictionary followed by one or two capitalized words, or preceded by one.

```
(?:^|(?<=\s)){FIRST_NAME}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b
```

Built as a Presidio recognizer that dynamically generates patterns from the dictionary at init time. Since ~1000 patterns in one regex alternation would be slow, instead implement as a custom `EntityRecognizer` (not `PatternRecognizer`) that:
1. Tokenizes text by whitespace
2. Checks each token against a set lookup
3. If matched, looks at adjacent tokens for capitalized words
4. Returns results with position spans

**Confidence:** 0.4
**Entity type:** `PERSON` (maps to `NAME`)

### 1c. Capitalized Word Pair Heuristic

**Pattern:** Two or more adjacent capitalized words that are not at the start of a sentence and are not common non-name phrases.

Implemented as a custom `EntityRecognizer` (not regex-only) that:
1. Finds all sequences of 2-3 adjacent capitalized words in the text
2. Checks preceding context programmatically to filter out sentence starts — accounts for period+space, newline, colon, bullet/dash markers, numbered list markers (`1. `), tab, `>` (quoted text), and start-of-text
3. Filters matches against an exclusion list stored as `pii_washer/data/capitalized_word_exclusions.json` containing: month names, day names, US state names, top 200 US city names, common organization suffixes (Inc, LLC, Corp, Ltd, Co, Foundation, Association, Institute, University, College, Hospital, etc.), country names, language names, and common two-word non-name phrases
4. Returns remaining matches as potential names

The exclusion list will need iterative tuning as false positives are discovered in real usage. It lives in a data file (not code constants) so it can be updated without code changes.

**Confidence:** 0.3
**Entity type:** `PERSON` (maps to `NAME`)

### Deduplication

All three layers feed into Presidio's standard analyzer pipeline. Presidio's built-in deduplication handles overlaps — if spaCy NER already detected a name at the same span, the fallback result is dropped. If multiple fallbacks overlap, the highest-confidence one wins.

---

## 2. SSN Pattern Hardening

**Current:** Only matches `\d{3}-\d{2}-\d{4}` (dashed format).

**Add these formats:**

| Format | Example | Confidence |
|--------|---------|------------|
| Dashed (existing) | `123-45-6789` | 0.85 (existing) |
| Spaces | `123 45 6789` | 0.7 |
| No separators (context required) | `123456789` | 0.4 (only flagged when SSN keywords nearby) |
| Dots | `123.45.6789` | 0.65 |
| Mixed (any combo of space/dash/dot) | `123 45-6789`, `123.45 6789` | 0.6 |

**Validation rules (all formats):**
- First group: 3 digits, not `000`, not `666`, not `9xx`
- Second group: 2 digits, not `00`
- Third group: 4 digits, not `0000`

These are real SSA validation rules that reduce false positives.

**Context boosting:** If SSN-related keywords appear nearby ("SSN", "social security", "social sec", "SS#", "SS #"), boost confidence by +0.2 (capped at 1.0).

**Implementation:** Replace the single Presidio built-in US_SSN recognizer with a custom `PatternRecognizer` that includes all format variants.

---

## 3. Phone Number Pattern Hardening

**Current:** Matches parentheses, dashes, +1 prefix.

**Add these formats:**

| Format | Example | Confidence |
|--------|---------|------------|
| Dots | `555.867.5309` | 0.65 |
| Spaces | `555 867 5309` | 0.55 |
| No separators (context required) | `5558675309` | 0.4 (only flagged when phone keywords nearby: call, phone, tel, cell, mobile, fax, contact) |
| Mixed separators | `(555) 867.5309` | 0.65 |
| With country code variations | `1-555-867-5309`, `+1.555.867.5309` | 0.7 |
| With extension | `555-867-5309 ext 123`, `555-867-5309 x123` | 0.7 |

**Validation rules:**
- Area code: 3 digits, first digit 2-9
- Exchange: 3 digits, first digit 2-9
- Subscriber: 4 digits

**Implementation:** Custom `PatternRecognizer` replacing or supplementing the built-in `PHONE_NUMBER` recognizer.

---

## 4. Address Pattern Hardening

**Current:** Matches house number + optional directional + 1-4 street name words + street type suffix.

**Add:**

| Pattern | Example | Confidence |
|---------|---------|------------|
| Apartment/suite/unit | `123 Main St Apt 4B`, `123 Main St #4B`, `Suite 200` | Same as base address |
| PO Box | `P.O. Box 123`, `PO Box 123`, `POB 123`, `Post Office Box 123` | 0.7 |
| Common street type misspellings | `Steet`, `Stret`, `Avnue`, `Aveneue`, `Bulevard`, `Bouelvard` | 0.5 (lower due to uncertain match, excludes real English words) |
| Highway addresses | `123 Highway 101`, `123 Hwy 101`, `123 Route 66`, `123 Rte 66` | 0.65 |

**Implementation:** Extend the existing `US_STREET_ADDRESS` pattern recognizer with additional patterns. Add a new `US_PO_BOX` pattern recognizer. `US_PO_BOX` maps to `ADDRESS` in `ENTITY_MAPPING`.

---

## 5. Credit Card Pattern Hardening

**Current:** Matches dashed format (`4111-1111-1111-1111`).

**Add these formats:**

| Format | Example | Confidence |
|--------|---------|------------|
| Spaces | `4111 1111 1111 1111` | 0.75 |
| No separators | `4111111111111111` | 0.5 |
| Dots | `4111.1111.1111.1111` | 0.6 |

**Validation:** Luhn algorithm check on all formats. Presidio's built-in `CreditCardRecognizer` is a subclass with custom Luhn logic, not a plain `PatternRecognizer`. The implementation should either subclass `CreditCardRecognizer` to add new patterns, or implement a custom `EntityRecognizer` that includes Luhn validation in its `analyze()` method.

**Implementation:** Custom recognizer extending or wrapping Presidio's built-in `CreditCardRecognizer`.

---

## 6. IP Address Enhancement

**Current:** IPv4 only (e.g., `192.168.1.1`).

**Add:**

| Pattern | Example | Confidence |
|---------|---------|------------|
| IPv4 with port | `192.168.1.1:8080` | 0.65 |
| IPv6 full | `2001:0db8:85a3:0000:0000:8a2e:0370:7334` | 0.7 |
| IPv6 compressed | `2001:db8::8a2e:370:7334` | 0.65 |
| IPv6 loopback/link-local excluded | `::1`, `fe80::` | Not flagged |

**Implementation:** Custom `PatternRecognizer` supplementing the built-in `IP_ADDRESS` recognizer.

---

## 7. Email Enhancement

**Current:** Presidio built-in email detection.

**Add:**

| Pattern | Example | Confidence |
|---------|---------|------------|
| Plus addressing | `user+tag@gmail.com` | 0.85 |
| Subdomain emails | `user@mail.company.com` | 0.85 |
| Obfuscated "at" | `user [at] gmail.com`, `user(at)gmail.com` | 0.5 |
| Obfuscated "dot" | `user@gmail [dot] com`, `user@gmail(dot)com` | 0.5 |

**Implementation:** Custom `PatternRecognizer` supplementing the built-in `EMAIL_ADDRESS` recognizer.

---

## 8. Context Filter Loosening

### DOB/Date Detection

**Current:** Requires keywords ("born", "birthday", etc.) within 50 chars.

**Changes:**
- Expand keyword list: add "d.o.b", "b.", "born on", "birth year", "age:", "age :", "DOB:", "Date of Birth:"
- Increase context window: 50 -> 100 characters
- Add low-confidence keywordless detection: dates in MM/DD/YYYY, Month DD YYYY, and MM-DD-YYYY formats flagged at confidence 0.2 even without keywords (user can reject during review)

### ZIP Code Detection

**Current:** 5-digit ZIPs need state abbreviation or street type within 100 chars.

**Changes:**
- Increase context window: 100 -> 150 characters
- Add city names as valid context (top 200 US cities)
- Add "zip", "zip code", "postal", "postal code" as valid context keywords

### URL PII Detection

**Current:** Only flags 6 social platforms (LinkedIn, Facebook, GitHub, Twitter/X, Instagram).

**Changes:**
- Add platforms: Reddit, TikTok, Medium, YouTube, Pinterest, Tumblr, Mastodon, Threads, Bluesky, Stack Overflow, GitLab, Bitbucket
- Add profile path heuristic: flag URLs containing patterns like `/user/`, `/u/`, `/profile/`, `/~`, `/people/`, `/@` followed by what looks like a username (alphanumeric + hyphens/underscores, not another path word like "settings" or "update") at confidence 0.4

---

## 9. Architecture

### No new dependencies

All changes use existing Presidio recognizer patterns and spaCy. The only new asset is the Census name list JSON file.

### New files

| File | Purpose |
|------|---------|
| `pii_washer/data/common_first_names.json` | Census-derived first name list (~1000 names) |
| `pii_washer/data/us_cities_top200.json` | Top 200 US city names for ZIP context matching |
| `pii_washer/name_recognizer.py` | Custom Presidio `EntityRecognizer` for dictionary-based name detection |
| `pii_washer/data/capitalized_word_exclusions.json` | Exclusion list for capitalized word pair heuristic (month/day names, cities, states, org suffixes, etc.) |

### Modified files

| File | Changes |
|------|---------|
| `pii_washer/pii_detection_engine.py` | Register new recognizers, update context filters, add new patterns, update constants, add `ENTITY_MAPPING` entries for `US_PO_BOX` -> `ADDRESS` |
| `pii_washer/tests/test_pii_detection_engine.py` | New test cases for all new patterns and formats |

### Recognizer registration

All new recognizers are instantiated in `PIIDetectionEngine.__init__()` and added to the Presidio analyzer registry, following the existing pattern used by the street address and ZIP code recognizers.

### Data file loading

Name dictionary and city list loaded once at `__init__()` time. Files are small (~30KB combined) so no lazy loading needed.

---

## 10. Testing Strategy

### New test categories

For each category (SSN, phone, address, CCN, IP, email), add:
- **Format variant tests:** Each new format detected correctly
- **Confidence level tests:** Looser formats get lower confidence
- **Validation tests:** Invalid values rejected (e.g., SSN starting with 000)
- **False positive tests:** Things that look like PII but aren't (9-digit order numbers, 10-digit ISBN, etc.)

### Name detection tests

- Title + name combinations (all title variants)
- Dictionary name + surname combinations
- Capitalized word pairs that ARE names
- Capitalized word pairs that AREN'T names (month names, company names, city names)
- Overlap with spaCy NER (no duplicates)
- Case sensitivity (dictionary lookup should be case-insensitive for first names)

### Context filter tests

- DOB with expanded keywords
- DOB without keywords (low confidence detection)
- ZIP with city name context
- ZIP with "zip code" keyword context
- URL with new social platforms
- URL with profile path patterns

### Integration tests

- Documents with multiple PII types in new formats
- Mixed old-format and new-format PII in same document
- High false-positive-risk documents (financial reports with lots of numbers)

---

## 11. Confidence Tier Summary

| Tier | Confidence | Meaning |
|------|-----------|---------|
| High | 0.7 - 0.85 | Strong structural match (title + name, dashed SSN, full phone with country code) |
| Medium | 0.5 - 0.65 | Reasonable match with some ambiguity (dot-separated SSN, PO Box, obfuscated email) |
| Low | 0.3 - 0.4 | Speculative match (capitalized word pairs, no-separator numbers, keywordless dates) |
| Very low | 0.2 | Wide-net catch (dates without context keywords) |

The default confidence threshold changes from 0.3 to 0.2, consistent with the "catch more, review more" philosophy. This means keywordless date detection and all other low-confidence matches surface for user review. If false positives prove too noisy in practice, we dial the threshold back up.

---

## 12. Performance

Adding new recognizers and wider patterns increases per-document analysis time. Run before/after benchmarks on representative documents (1-page letter, 3-page medical record, 5-page contract) to confirm latency stays acceptable. The name dictionary set lookup is O(1) per token, so the main cost is additional regex passes. Target: no more than 2x slowdown from current baseline.

---

## 13. What This Does NOT Cover

- International PII formats (deferred)
- UI changes for reviewing more detections (separate roadmap item)
- New entity types (only improving existing 9 categories)
- spaCy model replacement (staying with `en_core_web_lg`)
- Runtime-configurable recognizers (hardcoded at init, as today)
